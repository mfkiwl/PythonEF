"""Bi fixed beam"""

import matplotlib.pyplot as plt
import numpy as np
from Interface_Gmsh import Interface_Gmsh, ElemType, Line, Point, PointsList
import Display
import Materials
import Simulations
import Folder
import PostProcessing

if __name__ == '__main__':

    Display.Clear()

    # --------------------------------------------------------------------------------------------
    # Dimensions
    # --------------------------------------------------------------------------------------------

    L = 120
    nL = 10
    h = 20
    b = 13
    e = 2
    E = 210000
    v = 0.3
    load = 800

    # --------------------------------------------------------------------------------------------
    # Section
    # --------------------------------------------------------------------------------------------
    
    def DoSym(p: Point, n: np.ndarray) -> Point:
        pc = p.copy()
        pc.symmetry(n=n)
        return pc

    p1 = Point(-b/2,-h/2)
    p2 = Point(b/2,-h/2)
    p3 = Point(b/2,-h/2+e)
    p4 = Point(e/2,-h/2+e, r=e)
    p5 = DoSym(p4,(0,1))
    p6 = DoSym(p3,(0,1))
    p7 = DoSym(p2,(0,1))
    p8 = DoSym(p1,(0,1))
    p9 = DoSym(p6,(1,0))
    p10 = DoSym(p5,(1,0))
    p11 = DoSym(p4,(1,0))
    p12 = DoSym(p3,(1,0))
    contour = PointsList([p1,p2,p3,p4,p5,p6,p7,p8,p9,p10,p11,p12],e/6)    
    section = Interface_Gmsh().Mesh_2D(contour)
    
    ax = Display.Plot_Mesh(section)
    ax.set_title('Section')

    # --------------------------------------------------------------------------------------------
    # Mesh
    # --------------------------------------------------------------------------------------------

    elemType = ElemType.SEG2
    beamDim = 2

    point1 = Point()
    point2 = Point(x=L / 2)
    point3 = Point(x=L)
    line1 = Line(point1, point2, L / nL)
    line2 = Line(point2, point3, L / nL)
    line = Line(point1, point3)
    beam1 = Materials.Beam_Elas_Isot(beamDim, line1, section, E, v)
    beam2 = Materials.Beam_Elas_Isot(beamDim, line2, section, E, v)
    beams = [beam1, beam2]

    mesh = Interface_Gmsh().Mesh_Beams(beams=beams, elemType=elemType)

    # --------------------------------------------------------------------------------------------
    # Simulation
    # --------------------------------------------------------------------------------------------

    # Initialize the beam structure with the defined beam segments
    beamStructure = Materials.Beam_Structure(beams)

    # Create the beam simulation
    simu = Simulations.Simu_Beam(mesh, beamStructure)
    dof_n = simu.Get_dof_n()

    # Apply boundary conditions
    simu.add_dirichlet(mesh.Nodes_Point(point1), [0]*dof_n, simu.Get_directions())
    simu.add_dirichlet(mesh.Nodes_Point(point3), [0]*dof_n, simu.Get_directions())
    simu.add_neumann(mesh.Nodes_Point(point2), [-load], ["y"])
    if beamStructure.nBeam > 1:
        simu.add_connection_fixed(mesh.Nodes_Point(point2))

    # Solve the beam problem and get displacement results
    sol = simu.Solve()
    simu.Save_Iter()
    
    # eps = simu._Calc_Epsilon_e_pg(sol)
    # forces = simu.Results_Nodes_Values(mesh, simu._Calc_InternalForces_e_pg(eps).mean(1))
    # sig = simu._Calc_Sigma_e_pg(eps)
    
    # print(forces[mesh.Nodes_Point(point2)])
    # print(simu.Result('rz')[mesh.Nodes_Point(point2)])

    # --------------------------------------------------------------------------------------------
    # Results
    # --------------------------------------------------------------------------------------------

    u_an = load * L**3 / (192*E*beam1.Iz)

    uy_1d = np.abs(simu.Result('uy').min())

    print(f"err beam model : {np.abs(u_an-uy_1d)/u_an*100:.2f} %")

    Display.Plot_BoundaryConditions(simu)
    Display.Plot_Mesh(simu, L/20/sol.min())
    Display.Plot_Result(simu, "uy", L/20/sol.min())    

    print(simu)

    plt.show()