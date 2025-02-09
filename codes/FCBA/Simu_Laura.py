import Display
from Geom import Point, PointsList, Circle, Domain, normalize_vect, Line
from Interface_Gmsh import Interface_Gmsh, ElemType, Mesh
import Materials
import Simulations
import Folder
import PostProcessing

import matplotlib.pyplot as plt
import numpy as np

Display.Clear()

folder_FCBA = Folder.New_File("FCBA",results=True)
folder = Folder.Join(folder_FCBA, "Compression_Laura")

def DoMesh(dim:int, L:float, H:float, D:float, h:float, D2:float, h2:float, t:float, l0:float, test:bool, optimMesh:bool) -> Mesh:

    clC = l0 if test else l0/2
    clD = clC*3 if optimMesh else clC

    if optimMesh:
        refineGeom = Domain(Point(L/2-D, 0, 0), Point(L/2+D, H, t), clC)
    else:
        refineGeom = None

    contour = Domain(Point(), Point(L,H), clD)
    circle = Circle(Point(L/2, H-h), D, clC, True)

    # Hole        
    p1 = Point(L/2, H-55, t/2)
    p2 = Point(L/2+D2/2, p1.y+D2/2, p1.z)
    p3 = Point(p2.x, H, p1.z)
    p4 = p3 - [D2/2]        
    hole = PointsList([p1,p2,p3,p4])
    axis = Line(p1,p4)
    # hole.Plot_Geoms([contour, circle, hole, axis])

    if dim == 2:
        mesh = Interface_Gmsh().Mesh_2D(contour, [circle], ElemType.TRI3, refineGeoms=[refineGeom])
        
    elif dim == 3:
        if D2 == 0:
            mesh = Interface_Gmsh().Mesh_3D(contour, [circle], [0,0,t], [4], ElemType.TETRA4, refineGeoms=[refineGeom])
        else:
            interf = Interface_Gmsh(False, False)
            fact = interf.factory

            # Box and cylinder
            surf1 = interf._Surfaces(contour, [circle])[0]
            vol1 = interf._Extrude(surf1, [0,0,t])
            # Hole
            surf2 = interf._Surfaces(hole)[0]
            vol2 = interf._Revolve(surf2, axis)
            
            fact.cut(vol1, [(ent) for ent in vol2 if ent[0] == 3])

            interf.Set_meshSize(clD)

            interf._RefineMesh([refineGeom], clD)

            interf._Set_PhysicalGroups()

            interf._Meshing(3, ElemType.TETRA4)

            mesh = interf._Construct_Mesh()

    return mesh

if __name__  == '__main__':

    # --------------------------------------------------------------------------------------------
    # Configuration
    # --------------------------------------------------------------------------------------------
    dim = 3

    test = True
    optimMesh = True
    loadInHole = True
    makeParaview = False

    # geom
    H = 120 # mm
    L = 90
    D = 10
    h = 35
    D2 = 7
    h2 = 55
    t = 20

    # nL = 50
    # l0 = L/nL
    l0 = 1
    nL = L//l0

    # --------------------------------------------------------------------------------------------
    # Mesh
    # --------------------------------------------------------------------------------------------
    
    mesh = DoMesh(dim, L, H, D, h, D2, h2, t, l0, test, optimMesh)

    Display.Plot_Mesh(mesh)
    print(mesh)

    # --------------------------------------------------------------------------------------------
    # Material
    # --------------------------------------------------------------------------------------------

    # Properties for test 4
    Gc = 0.075 # mJ/mm2

    psiC = (3*Gc)/(16*l0) 

    El = 15716.16722094732 
    Et = 232.6981580878141
    Gl = 557.3231495541391
    vl = 0.02
    vt = 0.44

    rot = 90 * np.pi/180
    axis_l = np.array([np.cos(rot), np.sin(rot), 0])
    axis_t = np.cross(np.array([0,0,1]), axis_l)

    split = "AnisotStress"
    regu = "AT1"

    comp = Materials.Elas_IsotTrans(dim, El, Et, Gl, vl, vt, axis_l, axis_t, True, t)
    pfm = Materials.PhaseField_Model(comp, split, regu, Gc, l0)

    # --------------------------------------------------------------------------------------------
    # Simulation
    # --------------------------------------------------------------------------------------------
    simu = Simulations.Simu_Displacement(mesh, comp)

    nodesLower = mesh.Nodes_Conditions(lambda x,y,z: y==0)

    if loadInHole:

        surf = np.pi * D/2 * t
        nodesLoad = mesh.Nodes_Cylinder(Circle(Point(L/2,H-h), D), [0,0,-t])
        nodesLoad = nodesLoad[mesh.coordo[nodesLoad,1] <= H-h]
        # Display.Plot_Nodes(mesh, nodesLoad)

        group = mesh.Get_list_groupElem(dim-1)[0]
        elems = group.Get_Elements_Nodes(nodesLoad)

        aire = np.einsum('ep,p->', group.Get_jacobian_e_pg("mass")[elems], group.Get_weight_pg("mass"))

        if dim == 2:
            aire *= t 

        print(f"errSurf = {np.abs(surf-aire)/surf:.3e}")

        def Eval(x: np.ndarray, y: np.ndarray, z: np.ndarray):
            """Evaluation of the sig cos(theta)^2 vect_n function\n
            x,y,z (ep)"""
            
            # Angle calculation
            theta = np.arctan((x-L/2)/(y-(H-h)))

            # Coordinates of Gauss points in matrix form
            coord = np.zeros((x.shape[0],x.shape[1],3))
            coord[:,:,0] = x
            coord[:,:,1] = y
            coord[:,:,2] = 0

            # Construction of the normal vector
            vect = coord - np.array([L/2, H-h,0])
            vectN = np.einsum('npi,np->npi', vect, 1/np.linalg.norm(vect, axis=2))
            
            # Loading
            loads = f/surf * np.einsum('np,npi->npi',np.cos(theta)**2, vectN)

            return loads

        EvalX = lambda x,y,z: Eval(x,y,z)[:,:,0]
        EvalY = lambda x,y,z: Eval(x,y,z)[:,:,1]    
        
        # ax = plt.subplots()[1]
        # ax.axis('equal')
        # angle = np.linspace(0, np.pi*2, 360)
        # ax.scatter(0,0,marker='+', c='black')
        # ax.plot(d/2*np.cos(angle),d/2*np.sin(angle), c="black")
        
        # sig = d/2
        # angle = np.linspace(0, np.pi, 21)

        # x = - d/2 * np.cos(angle)
        # y = - d/2 * np.sin(angle)

        # coord = np.zeros((x.size,2))
        # coord[:,0] = x; coord[:,1] = y
        # # ax.plot(x,y, c="red")

        # vectN = normalize_vect(coord)

        # f = sig * np.einsum("n,ni->ni", np.sin(angle)**2, vectN)
        # f[np.abs(f)<=1e-12] = 0

        # [ax.arrow(x[i], y[i], f[i,0], f[i,1], color='red', head_width=1e-1*2, length_includes_head=True) for i in range(angle.size)]
        # ax.plot((coord+f)[:,0], (coord+f)[:,1], c='red')
        # ax.set_axis_off()

        # Display.Save_fig(folder, 'illustration')

        # # ax.annotate("$x$",xy=(1,0),xytext=(0,0),arrowprops=dict(arrowstyle="->"), c='black')    

    else:
        surf = t * L
        nodesLoad = mesh.Nodes_Conditions(lambda x,y,z: y==H)

    # simu.Solve()

    array_f = np.linspace(0, 4, 10)*1000
    # array_f = np.array([2000])

    list_psiP = []

    for f in array_f:

        simu.Bc_Init()
        simu.add_dirichlet(nodesLower, [0]*dim, simu.Get_directions())
        if loadInHole:
            simu.add_surfLoad(nodesLoad, [EvalX, EvalY], ["x","y"],
                            description=r"$\mathbf{q}(\theta) = \sigma \ sin^2(\theta) \ \mathbf{n}(\theta)$")
        else:
            simu.add_surfLoad(nodesLoad, [-f/surf], ['y'])
        
        # solve and save iteraton
        simu.Solve()
        simu.Save_Iter()

        # Energy calculation
        Epsilon_e_pg = simu._Calc_Epsilon_e_pg(simu.displacement, "mass")
        psiP_e_pg, psiM_e_pg = pfm.Calc_psi_e_pg(Epsilon_e_pg)
        psiP_e = np.max(psiP_e_pg, axis=1)

        list_psiP.append(np.max(psiP_e))

        print(f"f = {f/1000:.3f} kN -> psiP/psiC = {list_psiP[-1]/psiC:.2e}")

    # --------------------------------------------------------------------------------------------
    # PostProcessing
    # --------------------------------------------------------------------------------------------
    if len(list_psiP) > 1:
        axLoad = plt.subplots()[1]
        axLoad.set_xlabel("$f \ [kN]$"); axLoad.set_ylabel("$\psi^+ \ / \ \psi_c$")
        axLoad.grid() 

        array_psiP = np.array(list_psiP)

        axLoad.plot([0,array_f[-1]/1000], [1, 1], zorder=3, c='black')
        axLoad.plot(array_f/1000, array_psiP/psiC, zorder=3, c='blue')
    
        Display.Save_fig(folder, "Load")

    Display.Plot_Mesh(mesh)
    ax = Display.Plot_BoundaryConditions(simu, folder=folder)
    # if dim == 2:    
    #     f_v = simu.Get_K_C_M_F()[0] @ simu.displacement
    #     f_m = f_v.reshape(-1,2)
    #     f_m *= 1
    #     nodes = np.concatenate([nodesLoad, nodesLower])
    #     xn,yn,zn = mesh.coordo[:,0], mesh.coordo[:,1], mesh.coordo[:,2]
    #     # ax.quiver(xn[nodes], yn[nodes], f_m[nodes,0], f_m[nodes,1], color='red', width=1e-3, scale=1e3)
    #     ax.quiver(xn, yn, f_m[:,0], f_m[:,1], color='red', width=1e-3, scale=1e4)

    Display.Plot_Result(simu, psiP_e, title="$\psi^+$", nodeValues=False)
    ax = Display.Plot_Result(simu, psiP_e/psiC, nodeValues=True, title="$\psi^+ \ / \ \psi_c$", colorbarIsClose=False)[1]

    elemtsDamage = np.where(psiP_e >= psiC)[0]
    if elemtsDamage.size > 0:
        nodes = np.unique(mesh.connect[elemtsDamage])
        # Display.Plot_Elements(mesh, nodes, alpha=0.2, edgecolor='black', ax=ax)
    Display.Save_fig(folder, "psiPpsiC")

    Display.Plot_Result(simu, "Sxx", plotMesh=False)
    Display.Plot_Result(simu, "Syy", plotMesh=False)
    Display.Plot_Result(simu, "Sxy", plotMesh=False)

    print(simu)

    if makeParaview:
        PostProcessing.Make_Paraview(folder, simu)

    plt.show()