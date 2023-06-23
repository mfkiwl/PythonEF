from scipy.optimize import least_squares
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import Simulations
import Folder
import Affichage
import Interface_Gmsh
import Materials
import Geom

Get_ddls_noeuds = Simulations.BoundaryCondition.Get_ddls_noeuds

Affichage.Clear()

# ----------------------------------------------
# Configuration
# ----------------------------------------------

folder = Folder.New_File("Identification", results=True)

# perturbations = [0.01, 0.02]
perturbations = np.linspace(0, 0.02, 4)
nTirage = 10

pltVerif = False
useRescale = True

l = 45
h = 90
b = 20
d = 10

meshSize = l/15
elemType = "TRI3"

mat = "bois" # "acier" "bois"

tol = 1e-10

f=40
sig = f/(l*b)

# ----------------------------------------------
# Maillage
# ----------------------------------------------

gmshInterface = Interface_Gmsh.Interface_Gmsh()

pt1 = Geom.Point()
pt2 = Geom.Point(l, 0)
pt3 = Geom.Point(l, h)
pt4 = Geom.Point(0, h)
points = Geom.PointsList([pt1, pt2, pt3, pt4], meshSize)

circle = Geom.Circle(Geom.Point(l/2, h/2), d, meshSize, isCreux=True)

mesh = gmshInterface.Mesh_2D(points, [circle], elemType)

# Affichage.Plot_Model(mesh)

nodesBord = mesh.Nodes_Tags(["L0", "L2"])
nodesp0 = mesh.Nodes_Tags(["P0"])
nodesBas = mesh.Nodes_Tags(["L0"])
nodesHaut = mesh.Nodes_Tags(["L2"])

ddlsX = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesBord, ["x"])
ddlsY = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesBord, ["y"])

assert nodesBord.size*2 == (ddlsX.size + ddlsY.size)

if useRescale:
    ddlsBasX = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesBas, ["x"])
    ddlsBasY = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesBas, ["y"])
    
    ddlsHautX = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesHaut, ["x"])
    ddlsHautY = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesHaut, ["y"])
    ddlsHautXY = Simulations.BoundaryCondition.Get_ddls_noeuds(2, "displacement", nodesHaut, ["x","y"])


# Affichage.Plot_Mesh(mesh)
# Affichage.Plot_Model(mesh)
# Affichage.Plot_Nodes(mesh, nodesX0)

# ----------------------------------------------
# Comportement
# ----------------------------------------------

tol0 = 1e-6
bSup = np.inf

if mat == "acier":
    E_exp, v_exp = 210000, 0.3
    comp = Materials.Elas_Isot(2, epaisseur=b)

    dict_param = {
        "E" : E_exp,
        "v" : v_exp
    }

    Emax=300000
    vmax=0.49
    E0, v0 = Emax, vmax
    x0 = [E0, v0]
    
    compIdentif = Materials.Elas_Isot(2, E0, v0, epaisseur=b)
    bounds=([tol0]*2, [bSup, vmax])

elif mat == "bois":
    EL_exp, GL_exp, ET_exp, vL_exp = 12000, 450, 500, 0.3

    dict_param = {
        "EL" : EL_exp,
        "GL" : GL_exp,
        "ET" : ET_exp,
        "vL" : vL_exp
    }
    
    EL0 = EL_exp * 10
    GL0 = GL_exp * 10
    ET0 = ET_exp * 10
    vL0 = vL_exp

    lb = [tol0]*4
    ub = (bSup, bSup, bSup, 0.5-tol0)
    bounds = (lb, ub)
    x0 = [EL0, GL0, ET0, vL0]

    comp = Materials.Elas_IsotTrans(2, El=EL_exp, Et=ET_exp, Gl=GL_exp, vl=vL_exp, vt=0.3,
    axis_l=np.array([0,1,0]), axis_t=np.array([1,0,0]), contraintesPlanes=True, epaisseur=b)

    compIdentif = Materials.Elas_IsotTrans(2, El=EL0, Et=ET0, Gl=GL0, vl=vL0, vt=0.3,
    axis_l=np.array([0,1,0]), axis_t=np.array([1,0,0]), contraintesPlanes=True, epaisseur=b)

# ----------------------------------------------
# Simulation et chargement
# ----------------------------------------------

simu = Simulations.Simu_Displacement(mesh, comp)

simu.add_dirichlet(nodesBas, [0], ["y"])
simu.add_dirichlet(nodesp0, [0], ["x"])
simu.add_surfLoad(nodesHaut, [-sig], ["y"])

# Affichage.Plot_BoundaryConditions(simu)

u_exp = simu.Solve()

# Affichage.Plot_Result(simu, "uy")
# Affichage.Plot_Result(simu, "Syy", coef=1/sig, nodeValues=False)
# Affichage.Plot_Result(simu, np.linalg.norm(vectRand.reshape((mesh.Nn), 2), axis=1), title="bruit")
# Affichage.Plot_Result(simu, u_exp.reshape((mesh.Nn,2))[:,1], title='uy bruit')
# simu.Resultats_Resume()

# ----------------------------------------------
# Identification
# ----------------------------------------------

Affichage.NewSection("Identification")

simuIdentif = Simulations.Simu_Displacement(mesh, compIdentif)

def func(x):
    # Fonction coût

    # Mise à jour des paramètres
    if mat == "acier":
        # x0 = [E0, v0]
        E = x[0]
        v = x[1]
        compIdentif.E = E
        compIdentif.v = v
    elif mat == "bois":
        # x0 = [EL0, GL0, ET0, vL0]
        compIdentif.El = x[0]
        compIdentif.Gl = x[1]
        compIdentif.Et = x[2]
        compIdentif.vl = x[3]

    simuIdentif.Need_Update()

    u = simuIdentif.Solve()
    
    diff = u - u_exp_bruit
    diff = diff[ddlsInconnues]

    return diff

def Add_Dirichlet(nodes: np.ndarray, directions=["x","y"]):
    """Ajoute les conditions de déplacements"""

    ddls = Get_ddls_noeuds(2, "displacement", nodes, directions)

    nDim = len(directions)

    values = u_exp_bruit[ddls]
    values = np.reshape(values, (-1,nDim))

    valeurs = [values[:,d] for d in range(nDim)]

    simuIdentif.add_dirichlet(nodes, valeurs, directions)

# liste de dictionnaire qui va contenir pour les différentes perturbations les
# propriétés identifiées

list_dict_perturbation = []

for perturbation in perturbations:

    print(f"\nperturbation = {perturbation}")

    list_dict_tirage = []

    for tirage in range(nTirage):

        print(f"tirage = {tirage}", end='\r')        

        # bruitage de la solution
        bruit = np.abs(u_exp).max() * (np.random.rand(u_exp.shape[0]) - 1/2) * perturbation
        u_exp_bruit = u_exp + bruit

        if mat == "acier":
            compIdentif.E = E0
            compIdentif.v = v0
        elif mat == "bois":
            compIdentif.El = EL0
            compIdentif.Gl = GL0
            compIdentif.Et = ET0
            compIdentif.vl = vL0

        simuIdentif.Bc_Init()
        
        if useRescale:

            # ici quand on bruite la solution le vecteur de force calculé n'est plus correct
            # l'indentifiacation en rescalant le vecteur ne peut donc pas fonctionner
            # il faut choisir l'option 2
            
            # optionRescale = 0 # dirichlet x et neumann sur y haut
            # optionRescale = 1 # dirichlet x,y bas et neumann x,y sur haut
            optionRescale = 2 # dirichlet x,y bas, dirichlet x haut et surfload y haut
            
            K = simuIdentif.Get_K_C_M_F("displacement")[0]

            if optionRescale == 0:
                # prends que les ddls suivant y
                f_ddls = K[ddlsHautY,:] @ u_exp_bruit
                f_r = f_ddls.copy()
            elif optionRescale == 1:
                # prends les ddls suivant x et y
                f_ddls = K[ddlsHautXY,:] @ u_exp_bruit
                f_ddls = f_ddls.reshape(-1,2)
                f_r = np.linalg.norm(f_ddls, axis=1)

            if optionRescale in [0, 1]:
                # suuumm = np.sum(f_num_ddls[:,1])

                correct = f / np.sum(f_r)

                f_ddls *= correct

                # suuumm = np.sum(f_num_ddls[:,1])

                verifF =  np.sum(f_r*correct) - f
                assert np.abs(verifF) <= 1e-10

            if optionRescale == 0:
                # applique sur les surfaces en contact avec les mors les déplacements suivant x 
                Add_Dirichlet(nodesBord, ['x'])
                # applique sur la surface inférieure les déplacements suivants y 
                Add_Dirichlet(nodesBas, ['y'])
                # applique sur la surface supérieure le vecteur de force corrigé suivant y
                simuIdentif.add_neumann(nodesHaut, [f_ddls], ["y"])

            elif optionRescale == 1:
                # applique sur les surfaces en contact avec le plateau inférieur
                Add_Dirichlet(nodesBas, ['x','y'])
                # applique sur la surface supérieure le vecteur de force corrigé suivant y
                simuIdentif.add_neumann(nodesHaut, [f_ddls[:,0], f_ddls[:,1]], ["x","y"])            

            elif optionRescale == 2:
                # applique sur les surfaces en contact avec le plateau inférieur
                Add_Dirichlet(nodesBas, ['x','y'])
                # applique les deplacements suivant y sur les noeuds du haut
                Add_Dirichlet(nodesHaut, ['x'])
                # applique la charge surfacique
                simuIdentif.add_surfLoad(nodesHaut, [-sig], ["y"])                
        else:
            # applique les ddls sur le bord
            Add_Dirichlet(nodesBord, ['x','y'])

        ddlsConnues, ddlsInconnues = simuIdentif.Bc_ddls_connues_inconnues(simuIdentif.problemType)
        # Affichage.Plot_BoundaryConditions(simuIdentif)

        # res = least_squares(func, x0, bounds=bounds, verbose=2, ftol=tol, gtol=tol, xtol=tol, jac='3-point')
        res = least_squares(func, x0, bounds=bounds, verbose=0, ftol=tol, gtol=tol, xtol=tol)

        dict_tirage = {
            "tirage" : tirage
        }

        if mat == "acier":
            dict_tirage["E"]=res.x[0]
            dict_tirage["v"]=res.x[1]
        elif mat == "bois":
            dict_tirage["EL"]=res.x[0]
            dict_tirage["GL"]=res.x[1]
            dict_tirage["ET"]=res.x[2]
            dict_tirage["vL"]=res.x[3]

        list_dict_tirage.append(dict_tirage)

    df_tirage = pd.DataFrame(list_dict_tirage)

    dict_perturbation = {
        "perturbation" : perturbation,
    }

    if mat == "acier":
        dict_perturbation["E"] = df_tirage["E"].values
        dict_perturbation["v"] = df_tirage["v"].values
    elif mat == "bois":
        dict_perturbation["EL"] = df_tirage["EL"].values
        dict_perturbation["GL"] = df_tirage["GL"].values
        dict_perturbation["ET"] = df_tirage["ET"].values
        dict_perturbation["vL"] = df_tirage["vL"].values

    list_dict_perturbation.append(dict_perturbation)
    

df_pertubation = pd.DataFrame(list_dict_perturbation)

# ----------------------------------------------
# Affichage
# ----------------------------------------------

if mat == "acier":
    params = ["E","v"]
elif mat == "bois":
    params = ["EL", "GL", "ET", "vL"]

borne = 0.95
bInf = 0.5 - (0.95/2)
bSup = 0.5 + (0.95/2)

for param in params:

    axParam = plt.subplots()[1]
    
    paramExp = dict_param[param]

    perturbations = df_pertubation["perturbation"]

    nPertu = perturbations.size
    values = np.zeros((nPertu, nTirage))
    for p in range(nPertu):
        values[p] = df_pertubation[param].values[p]
    
    print(f"{param} = {values.mean()}")

    values *= 1/paramExp

    mean = values.mean(axis=1)
    std = values.std(axis=1)

    paramInf, paramSup = tuple(np.quantile(values, (bInf, bSup), axis=1))

    axParam.plot(perturbations, [1]*nPertu, label=f"{param}_exp", c="black", ls='--')
    axParam.plot(perturbations, mean, label=f"{param}_moy")
    axParam.fill_between(perturbations, paramInf, paramSup, alpha=0.3, label=f"{borne*100} % ({nTirage} tirages)")
    axParam.set_xlabel("perturbations")
    axParam.set_ylabel(fr"${param} \ / \ {param}_{'{exp}'}$")
    axParam.grid()
    axParam.legend(loc="upper left")
    
    Affichage.Save_fig(folder, "FEMU_"+param, extension='pdf')

    


diff_n = np.reshape(simuIdentif.displacement - u_exp, (mesh.Nn, 2))

# err_n = np.linalg.norm(diff_n, axis=1)/np.linalg.norm(u_exp.reshape((mesh.Nn,2)), axis=1)
err_n = np.linalg.norm(diff_n, axis=1)/np.linalg.norm(u_exp)
# err_n = np.linalg.norm(diff_n, axis=1)

Affichage.Plot_Result(simuIdentif, err_n, title=r"$\dfrac{\Vert u(p) - u_{exp} \Vert^2}{\Vert u_{exp} \Vert^2}$")

# print(np.linalg.norm(diff_n)/np.linalg.norm(u_exp))

plt.show()
