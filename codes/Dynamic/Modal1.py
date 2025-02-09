from Interface_Gmsh import Interface_Gmsh, gmsh, Point, Domain, Line, ElemType
import Display
import Folder
import Simulations
import Materials
import PostProcessing

import sys
import os
from scipy.sparse import linalg, eye
import numpy as np

folder = Folder.Get_Path(__file__)

if __name__ == '__main__':

    Display.Clear()

    folderSave = Folder.New_File("ModalAnalysis",results=True)
    if not os.path.exists(folderSave): os.makedirs(folderSave)

    dim = 3

    isFixed = True

    if __name__ == '__main__':

        Display.Clear()

        contour = Domain(Point(), Point(1,1))
        thickness = 1/10

        if dim == 2:
            mesh = Interface_Gmsh().Mesh_2D(contour, [], ElemType.QUAD4, isOrganised=True)
        else:
            mesh = Interface_Gmsh().Mesh_3D(contour, [], [0,0,-thickness], [2], ElemType.HEXA8, isOrganised=True)
        nodesY0 = mesh.Nodes_Conditions(lambda x,y,z: y==0)
        nodesSupY0 = mesh.Nodes_Conditions(lambda x,y,z: y>0)

        Display.Plot_Mesh(mesh)

        material = Materials.Elas_Isot(dim, planeStress=True, thickness=thickness)

        simu = Simulations.Simu_Displacement(mesh, material)

        simu.Solver_Set_Newton_Raphson_Algorithm(0.1)

        K, C, M, F = simu.Get_K_C_M_F()
        
        if isFixed:
            simu.add_dirichlet(nodesY0, [0]*dim, simu.Get_directions())
            known, unknown = simu.Bc_dofs_known_unknow(simu.problemType)
            K_t = K[unknown, :].tocsc()[:, unknown].tocsr()
            M_t = M[unknown, :].tocsc()[:, unknown].tocsr()

        else:        
            K_t = K + K.min() * eye(K.shape[0]) * 1e-12
            M_t = M

        eigenValues, eigenVectors = linalg.eigs(K_t, 10, M_t, which="SM")

        eigenValues = np.array(eigenValues, dtype=float)
        eigenVectors = np.array(eigenVectors, dtype=float)

        freq_t = np.sqrt(eigenValues.real)/2/np.pi

        num = 0

        for n in range(eigenValues.size):

            if isFixed:
                mode = np.zeros((mesh.Nn, dim))
                mode[nodesSupY0,:] = np.reshape(eigenVectors[:,n], (-1, dim))
            else:
                mode = np.reshape(eigenVectors[:,n], (-1, dim))

            simu.set_u_n(simu.problemType, mode.reshape(-1))
            simu.Save_Iter()        

            sol = np.linalg.norm(mode, axis=1)
            deformFactor = 1/5/np.abs(sol).max() 
            Display.Plot_Mesh(simu, deformFactor, title=f'mode {n+1}')
            # Display.Plot_Result(simu, sol, deformFactor, title=f"mode {n}", plotMesh=True)
            pass

        axModes = Display.plt.subplots()[1]
        axModes.plot(np.arange(eigenValues.size), freq_t, ls='', marker='.')
        axModes.set_xlabel('modes')
        axModes.set_ylabel('freq [Hz]')

        # PostProcessing.Make_Paraview(folderSave, simu)
        



        # Display.Plot_Mesh(mesh)

        Display.plt.show()