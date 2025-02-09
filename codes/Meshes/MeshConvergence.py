from Geom import Domain, Point
from Mesh import Mesh
import Materials
from Interface_Gmsh import Interface_Gmsh, ElemType
import Simulations
import Display as Display
from TicTac import Tic
import Folder
import PostProcessing
import numpy as np
import matplotlib.pyplot as plt

if __name__ == '__main__':

    Display.Clear()

    # --------------------------------------------------------------------------------------------
    # Configuration
    # --------------------------------------------------------------------------------------------
    dim = 2 # Define the dimension of the problem (2D or 3D)

    isOrganised = True

    # List of mesh sizes (number of elements) to investigate convergence
    if dim == 2:
        list_N = np.arange(1, 16, 1)
    else:
        list_N = np.arange(1, 8, 2)

    # Create a folder to store the simulation results
    folder = Folder.New_File(Folder.Join("Mesh convergence",str(dim)+"D"), results=True)

    # Define whether to plot the results
    plotResult = True
    makeParaview = False

    # Define geometry parameters
    L = 120  # mm
    h = 13   # Height
    b = 13   # Width
    P = 800  # N

    # Material properties
    E = 210000  # MPa (Young's modulus)
    v = 0.25    # Poisson's ratio

    # Define the material behavior (elasticity with plane stress assumption)
    material = Materials.Elas_Isot(dim, thickness=b, E=E, v=v, planeStress=True)

    # Compute the theoretical deformation energy (reference value)
    WdefRef = 2 * P**2 * L / E / h / b * (L**2 / h / b + (1 + v) * 3 / 5)

    # Lists to store data for plotting
    times_elem_N = [] # times for element type and N size
    wDef_elem_N = [] # energy
    dofs_elem_N = [] # dofs
    zz1_elem_N = [] # zz1

    # --------------------------------------------------------------------------------------------
    # Simulation
    # --------------------------------------------------------------------------------------------

    # Loop over each element type for both 2D and 3D simulations
    elemTypes = ElemType.get_2D() if dim == 2 else ElemType.get_3D()

    # elemTypes = [elem.name for elem in elemTypes.copy()]

    interfaceGmsh = Interface_Gmsh()

    for e, elemType in enumerate(elemTypes):
        
        times_N = []
        wDef_N = []
        dofs_N = []
        zz1_N = []

        # Loop over each mesh size (number of elements)
        for N in list_N:
            
            meshSize = b / N

            # Define the domain for the mesh
            domain = Domain(Point(), Point(x=L, y=h), meshSize)

            # Generate the mesh using Gmsh
            if dim == 2:
                mesh = interfaceGmsh.Mesh_2D(domain, [], elemType, isOrganised=isOrganised)
                volume = mesh.area * material.thickness
            else:
                mesh = interfaceGmsh.Mesh_3D(domain, [], elemType=elemType, extrude=[0, 0, b], layers=[4], isOrganised=isOrganised)
                volume = mesh.volume
            # Ensure that the volume matches the expected value (L * h * b)
            assert np.abs(volume - (L * h * b)) / volume <= 1e-10

            # Define nodes on the left boundary (x=0) and right boundary (x=L)
            nodes_x0 = mesh.Nodes_Conditions(lambda x, y, z: x == 0)
            nodes_xL = mesh.Nodes_Conditions(lambda x, y, z: x == L)

            # Create or update the simulation object with the current mesh        
            if e == 0 and N == list_N[0]:
                simu = Simulations.Simu_Displacement(mesh, material, useIterativeSolvers=False)
            else:
                simu.Bc_Init()
                simu.mesh = mesh

            # Set displacement boundary conditions
            simu.add_dirichlet(nodes_x0, [0]*dim, simu.Get_directions())
            # Set surface load on the right boundary (y-direction)
            simu.add_surfLoad(nodes_xL, [-P / h / b], ["y"])

            tic = Tic()

            # Solve the simulation
            simu.Solve()
            simu.Save_Iter()

            time = tic.Tac("Resolutions", "Temps total", False)

            # Get the computed deformation energy
            Wdef = simu.Result("Wdef")

            # Store the results for the current mesh size
            times_N.append(time)
            wDef_N.append(Wdef)
            dofs_N.append(mesh.Nn * dim)
            zz1_N.append(simu.Result("ZZ1"))

            if elemType != mesh.elemType:
                print("Error in mesh generation")

            print(f"Elem: {mesh.elemType}, nby: {N:2}, Wdef = {np.round(Wdef, 3)}, "
                f"error = {np.abs(WdefRef - Wdef) / WdefRef:.2e}")

        # Store the results for the current element type
        times_elem_N.append(times_N)
        wDef_elem_N.append(wDef_N)
        dofs_elem_N.append(dofs_N)
        zz1_elem_N.append(zz1_N)

    # --------------------------------------------------------------------------------------------
    # PostProcessing
    # --------------------------------------------------------------------------------------------
    # Display the convergence of deformation energy
    ax_Wdef = plt.subplots()[1]
    ax_error = plt.subplots()[1]
    ax_times = plt.subplots()[1]
    ax_zz1 = plt.subplots()[1]

    WdefRefArray = np.ones_like(dofs_elem_N[0]) * WdefRef
    WdefRefArray5 = WdefRefArray * 0.95

    print(f"\nWSA = {np.round(WdefRef, 4)} mJ")

    for e, elemType in enumerate(elemTypes):
        # Convergence of deformation energy
        ax_Wdef.plot(dofs_elem_N[e], wDef_elem_N[e])

        # Error in deformation energy
        Wdef = np.array(wDef_elem_N[e])
        erreur = (WdefRef - Wdef) / WdefRef * 100
        ax_error.loglog(dofs_elem_N[e], erreur)

        # Computation time
        ax_times.loglog(dofs_elem_N[e], times_elem_N[e])
        # ax_Times.plot(listDofs_e_nb[e], listTimes_e_nb[e])
        # ax_Times.set_xscale('log')

        # ZZ1
        # ax_zz1.loglog(dofs_elem_N[e], zz1_elem_N[e])
        ax_zz1.loglog(dofs_elem_N[e], zz1_elem_N[e])
        # ax_zz1.loglog(dofs_elem_N[e], erreur)
        # pass

    # Deformation energy
    ax_Wdef.grid()
    ax_Wdef.set_xlim([-10, 8000])
    ax_Wdef.set_xlabel('Degrees of Freedom (DOF)')
    ax_Wdef.set_ylabel('Strain energy (Wdef) [mJ]')
    ax_Wdef.legend(elemTypes)
    ax_Wdef.fill_between(dofs_N, WdefRefArray, WdefRefArray5, alpha=0.5, color='red')
    plt.figure(ax_Wdef.figure)
    Display.Save_fig(folder, 'Energy')

    # Error in deformation energy
    ax_error.grid()
    ax_error.set_xlabel('Degrees of Freedom (DOF)')
    ax_error.set_ylabel('Error Wdef [%]')
    ax_error.legend(elemTypes)
    plt.figure(ax_error.figure)
    Display.Save_fig(folder, 'Error')

    # Error in deformation energy
    ax_zz1.grid()
    ax_zz1.set_xlabel('Degrees of Freedom (DOF)')
    ax_zz1.set_ylabel('Error ZZ1 [%]')
    ax_zz1.legend(elemTypes)
    plt.figure(ax_error.figure)
    Display.Save_fig(folder, 'Error ZZ1')

    # Computation time
    ax_times.grid()
    ax_times.set_xlabel('Degrees of Freedom (DOF)')
    ax_times.set_ylabel('Computation Time [s]')
    ax_times.legend(elemTypes)
    plt.figure(ax_times.figure)
    Display.Save_fig(folder, 'Time')

    # Plot the von Mises stress result using 20 color levels
    Display.Plot_Result(simu, "Svm", nColors=20)

    if makeParaview:
        # Generate Paraview files for visualization
        PostProcessing.Make_Paraview(folder, simu, details=True)

    # Show the total computation time
    print()
    Tic.Resume()

    # Display the computation time history
    # Tic.Plot_History(folder)

    # Show all plots
    plt.show()