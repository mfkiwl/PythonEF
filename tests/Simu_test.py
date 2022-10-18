import unittest
from Materials import LoiDeComportement, Materiau, Elas_Isot, PhaseFieldModel, ThermalModel, BeamModel
from typing import cast
from Geom import Domain, Circle, Point, Poutre, Section, Line
import numpy as np
import Affichage as Affichage
from Mesh import Mesh
from Interface_Gmsh import Interface_Gmsh
from Simu import Simu
from TicTac import Tic
import matplotlib.pyplot as plt

class Test_Simu(unittest.TestCase):    
    
    def CreationDesSimusElastique(self):
        
        dim = 2

        # Paramètres géométrie
        L = 120;  #mm
        h = 120;    
        b = 13

        # Charge a appliquer
        P = -800 #N

        # Paramètres maillage
        taille = L/2

        

        self.simulationsElastique = []

        listMesh = Interface_Gmsh.Construction2D(L=L, h=h, taille=taille)
        listMesh.extend(Interface_Gmsh.Construction3D(L=L, h=h, b=b, taille=h/2))

        # Pour chaque type d'element 2D       
        for mesh in listMesh:           

            assert isinstance(mesh, Mesh)

            dim = mesh.dim

            comportement = Elas_Isot(dim, epaisseur=b)

            materiau = Materiau(comportement, verbosity=False)
            
            simu = Simu(mesh, materiau, verbosity=False)

            simu.Assemblage_u()

            noeuds_en_0 = mesh.Nodes_Conditions(conditionX=lambda x: x == 0)
            noeuds_en_L = mesh.Nodes_Conditions(conditionX=lambda x: x == L)

            simu.add_dirichlet("displacement", noeuds_en_0, [0, 0], ["x","y"], description="Encastrement")
            # simu.add_lineLoad("displacement",noeuds_en_L, [-P/h], ["y"])
            simu.add_dirichlet("displacement",noeuds_en_L, [lambda x,y,z: 1], ['x'])
            simu.add_surfLoad("displacement",noeuds_en_L, [P/h/b], ["y"])

            self.simulationsElastique.append(simu)
    
    def CreationDesSimusThermique(self):

        a = 1

        listMesh = Interface_Gmsh.Construction2D(L=a, h=a, taille=a/10)

        listMesh.extend(Interface_Gmsh.Construction3D(L=a, h=a, b=a, taille=a/10))

        self.simulationsThermique = []

        for mesh in listMesh:

            assert isinstance(mesh, Mesh)

            dim = mesh.dim

            thermalModel = ThermalModel(dim=dim, k=1, c=1, epaisseur=a)

            materiau = Materiau(thermalModel, verbosity=False)

            simu = Simu(mesh , materiau, False)

            noeuds0 = mesh.Nodes_Conditions(lambda x: x == 0)
            noeudsL = mesh.Nodes_Conditions(lambda x: x == a)
            
            simu.add_dirichlet("thermal", noeuds0, [0], [""])
            simu.add_dirichlet("thermal", noeudsL, [40], [""])

            self.simulationsThermique.append(simu)

    def test_SimulationsPoutreUnitaire(self):
        
        interfaceGmsh = Interface_Gmsh(False, False, False)

        listProblem = ["Flexion","Traction","BiEnca"]
        listElemType = ["SEG2","SEG3"]
        listBeamDim = [1,2,3]

        # Géneration des configs
        listConfig = [(problem, elemType, beamDim) for problem in listProblem for elemType in listElemType for beamDim in listBeamDim]

        def PlotAndDelete():
            plt.pause(1e-12)
            plt.close('all')
            

        for problem, elemType, beamDim in listConfig:
            
            if problem in ["Flexion","BiEnca"] and beamDim == 1:
                # Exclusion des configs impossible
                continue

            if problem in ["Flexion","BiEnca"]:
                L=120; nL=10
                h=13
                b=13
                E = 210000
                v = 0.3
                charge = 800    

            elif problem == "Traction":
                L=10 # m
                nL=10

                h=0.1
                b=0.1
                E = 200000e6
                ro = 7800
                v = 0.3
                g = 10
                q = ro * g * (h*b)
                charge = 5000
            
            # SECTION

            section = Section(interfaceGmsh.Rectangle_2D(Domain(Point(x=-b/2, y=-h/2), Point(x=b/2, y=h/2))))

            self.assertTrue((section.aire - b*h) <= 1e-12)
            self.assertTrue((section.Iz - ((b*h**3)/12)) <= 1e-12)

            # MAILLAGE

            if problem in ["Traction"]:

                point1 = Point()
                point2 = Point(x=L)
                line = Line(point1, point2, L/nL)
                poutre = Poutre(line, section)
                listePoutre = [poutre]

            elif problem in ["Flexion","BiEnca"]:

                point1 = Point()
                point2 = Point(x=L/2)
                point3 = Point(x=L)
                
                line = Line(point1, point3, L/nL)
                poutre = Poutre(line, section)
                listePoutre = [poutre]

            mesh = interfaceGmsh.Mesh_From_Lines_1D(listPoutres=listePoutre, elemType=elemType)

            # Modele poutre

            beamModel = BeamModel(dim=beamDim, listePoutres=listePoutre, list_E=[E]*len(listePoutre), list_v=[v]*len(listePoutre))

            materiau = Materiau(beamModel, verbosity=False)

            # Simulation

            simu = Simu(mesh, materiau, verbosity=False)

            # Conditions

            if beamModel.dim == 1:
                simu.add_dirichlet("beam", mesh.Nodes_Point(point1),[0],["x"])
                if problem == "BiEnca":
                    simu.add_dirichlet("beam", mesh.Nodes_Point(point3),[0],["x"])
            elif beamModel.dim == 2:
                simu.add_dirichlet("beam", mesh.Nodes_Point(point1),[0,0,0],["x","y","rz"])
                if problem == "BiEnca":
                    simu.add_dirichlet("beam", mesh.Nodes_Point(point3),[0,0,0],["x","y","rz"])
            elif beamModel.dim == 3:
                simu.add_dirichlet("beam", mesh.Nodes_Point(point1),[0,0,0,0,0,0],["x","y","z","rx","ry","rz"])
                if problem == "BiEnca":
                    simu.add_dirichlet("beam", mesh.Nodes_Point(point3),[0,0,0,0,0,0],["x","y","z","rx","ry","rz"])

            if problem == "Flexion":
                simu.add_pointLoad("beam", mesh.Nodes_Point(point3), [-charge],["y"])
                # simu.add_surfLoad("beam", mesh.Nodes_Point(point2), [-charge/section.aire],["y"])
                
            elif problem == "BiEnca":
                simu.add_pointLoad("beam", mesh.Nodes_Point(point2), [-charge],["y"])
            elif problem == "Traction":
                noeudsLine = mesh.Nodes_Line(line)
                simu.add_lineLoad("beam", noeudsLine, [q],["x"])
                simu.add_pointLoad("beam", mesh.Nodes_Point(point2), [charge],["x"])

            simu.Assemblage_beam()

            simu.Solve_beam()

            Affichage.Plot_BoundaryConditions(simu)
            PlotAndDelete()
            Affichage.Plot_Result(simu, "u", affichageMaillage=False, deformation=False)
            PlotAndDelete()
            if beamModel.dim > 1:
                Affichage.Plot_Result(simu, "v", affichageMaillage=False, deformation=False)
                PlotAndDelete()
                Affichage.Plot_Maillage(simu, deformation=True, facteurDef=10)
                PlotAndDelete()

        
            u = simu.Get_Resultat("u", valeursAuxNoeuds=True)
            if beamModel.dim > 1:
                v = simu.Get_Resultat("v", valeursAuxNoeuds=True)
                rz = simu.Get_Resultat("rz", valeursAuxNoeuds=True)

            listX = np.linspace(0,L,100)
            if problem == "Flexion":
                v_x = charge/(E*section.Iz) * (listX**3/6 - (L*listX**2)/2)
                flecheanalytique = charge*L**3/(3*E*section.Iz)

                self.assertTrue((np.abs(flecheanalytique + v.min())/flecheanalytique) <= 1e-12)

                fig, ax = plt.subplots()
                ax.plot(listX, v_x, label='Analytique', c='blue')
                ax.scatter(mesh.coordo[:,0], v, label='EF', c='red', marker='x', zorder=2)
                ax.set_title(fr"$v(x)$")
                ax.legend()
                PlotAndDelete()

                rz_x = charge/E/section.Iz*(listX**2/2 - L*listX)
                rotalytique = -charge*L**2/(2*E*section.Iz)
                self.assertTrue((np.abs(rotalytique + rz.min())/rotalytique) <= 1e-12)


                fig, ax = plt.subplots()
                ax.plot(listX, rz_x, label='Analytique', c='blue')
                ax.scatter(mesh.coordo[:,0], rz, label='EF', c='red', marker='x', zorder=2)
                ax.set_title(fr"$r_z(x)$")
                ax.legend()
                PlotAndDelete()
            elif problem == "Traction":
                u_x = (charge*listX/(E*(section.aire))) + (ro*g*listX/2/E*(2*L-listX))

                self.assertTrue((np.abs(u_x[-1] - u.max())/u_x[-1]) <= 1e-12)

                fig, ax = plt.subplots()
                ax.plot(listX, u_x, label='Analytique', c='blue')
                ax.scatter(mesh.coordo[:,0], u, label='EF', c='red', marker='x', zorder=2)
                ax.set_title(fr"$u(x)$")
                ax.legend()
                PlotAndDelete()

    def setUp(self):
        self.CreationDesSimusElastique()
        self.CreationDesSimusThermique()
        # TODO rajouter simulation endommagement !
        pass

    def test_ResolutionDesSimulationsElastique(self):
        # Pour chaque type de maillage on simule
        for simu in self.simulationsElastique:
            simu = cast(Simu, simu)

            simu.Assemblage_u(steadyState=False)

            simu.Solve_u(steadyState=True)
            fig, ax, cb = Affichage.Plot_Result(simu, "dx", affichageMaillage=True)
            plt.pause(1e-12)
            plt.close(fig)
            
            simu.Set_Hyperbolic_AlgoProperties(dt=0.5)
            simu.Solve_u(steadyState=False)
            fig, ax, cb = Affichage.Plot_Result(simu, "ax", affichageMaillage=True)
            plt.pause(1e-12)
            plt.close(fig)

    def test_ResolutionDesSimulationsThermique(self):
        # Pour chaque type de maillage on simule
        
        for simu in self.simulationsThermique:
            simu = cast(Simu, simu)
            
            N = len(simu.results)

            fig, ax, cb = Affichage.Plot_Result(simu, "thermal", valeursAuxNoeuds=True, affichageMaillage=True)

            Tmax = 1
            N = 2
            dt = Tmax/N
            t = 0

            simu.Set_Parabolic_AlgoProperties(alpha=0.5, dt=0.1)
            
            while t < Tmax:

                simu.Assemblage_t(steadyState=False)

                simu.Solve_t(steadyState=False)

                cb.remove()
                fig, ax, cb = Affichage.Plot_Result(simu, "thermal", valeursAuxNoeuds=True, affichageMaillage=True, oldfig=fig, oldax=ax)
                plt.pause(1e-12)

                simu.Save_Iteration()

                t += dt

            plt.close(fig)

    def test__ConstruitMatElem_Dep(self):
        for simu in self.simulationsElastique:
            simu = cast(Simu, simu)
            Ke_e = simu.ConstruitMatElem_Dep()
            self.__VerificationConstructionKe(simu, Ke_e)

    # ------------------------------------------- Vérifications ------------------------------------------- 

    def __VerificationConstructionKe(self, simu: Simu, Ke_e, d=[]):
            """Ici on verifie quon obtient le meme resultat quavant verification vectorisation

            Parameters
            ----------
            Ke_e : nd.array par element
                Matrice calculé en vectorisant        
            d : ndarray
                Champ d'endommagement
            """

            tic = Tic()

            matriceType = "rigi"

            # Data
            mesh = simu.mesh
            nPg = mesh.Get_nPg(matriceType)
            listPg = list(range(nPg))
            Ne = mesh.Ne            
            materiau = simu.materiau
            C = materiau.comportement.get_C()

            listKe_e = []

            B_dep_e_pg = mesh.Get_B_dep_e_pg(matriceType)            

            jacobien_e_pg = mesh.Get_jacobien_e_pg(matriceType)
            poid_pg = mesh.Get_poid_pg(matriceType)
            for e in range(Ne):            
                # Pour chaque poing de gauss on construit Ke
                Ke = 0
                for pg in listPg:
                    jacobien = jacobien_e_pg[e,pg]
                    poid = poid_pg[pg]
                    B_pg = B_dep_e_pg[e,pg]

                    K = jacobien * poid * B_pg.T.dot(C).dot(B_pg)

                    if len(d)==0:   # probleme standart
                        
                        Ke += K
                    else:   # probleme endomagement
                        
                        de = np.array([d[mesh.connect[e]]])
                        
                        # Bourdin
                        g = (1-mesh.N_mass_pg[pg].dot(de))**2
                        # g = (1-de)**2
                        
                        Ke += g * K
                # # print(Ke-listeKe[e.id])
                if mesh.dim == 2:
                    listKe_e.append(Ke)
                else:
                    listKe_e.append(Ke)                

            tic.Tac("Matrices","Calcul des matrices elementaires (boucle)", False)
            
            # Verification
            Ke_comparaison = np.array(listKe_e)*simu.materiau.comportement.epaisseur
            test = Ke_e - Ke_comparaison

            test = np.testing.assert_array_almost_equal(Ke_e, Ke_comparaison, verbose=False)

            self.assertIsNone(test)
            

if __name__ == '__main__':        
    try:
        Affichage.Clear()
        unittest.main(verbosity=2)    
    except:
        print("")   
