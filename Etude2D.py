# %%

from Geom import Domain, Point
import Dossier
import PostTraitement

from Materiau import Elas_Isot, Materiau
from Geom import *
from Interface_Gmsh import Interface_Gmsh
from Mesh import Mesh
from Simu import Simu
from Affichage import Affichage


import numpy as np
import matplotlib.pyplot as plt

from TicTac import TicTac

Affichage.Clear()

ticTot = TicTac()

# Data --------------------------------------------------------------------------------------------

plotResult = True

saveParaview = False

dim = 2

# Paramètres géométrie
L = 120;  #mm
h = 13
b = 13

P = 800 #N
lineLoad = P/h #N/mm

# Paramètres maillage
taille = h/2

comportement = Elas_Isot(dim, epaisseur=b, useVoigtNotation=True)

# Materiau
materiau = Materiau(comportement)

# Construction du modele et du maillage --------------------------------------------------------------------------------
elemType = "TRI3" # ["TRI3", "TRI6", "QUAD4", "QUAD8"]

domain = Domain(Point(), Point(x=L, y=h))

interfaceGmsh = Interface_Gmsh()
mesh = interfaceGmsh.ConstructionRectangle(domain=domain, elemType=elemType, tailleElement=taille, isOrganised=False)

# Récupère les noeuds qui m'interessent

noeuds_en_0 = mesh.Get_Nodes_Line(Line(Point(), Point(y=h)))  # noeuds_en_0 = mesh.Get_Nodes_Conditions(conditionX=lambda x: x == 0)
noeuds_en_L = mesh.Get_Nodes_Line(Line(Point(x=L), Point(x=L, y=h)))       # noeuds_en_L = mesh.Get_Nodes_Conditions(conditionX=lambda x: x == L)

# ------------------------------------------------------------------------------------------------------
Affichage.NouvelleSection("Traitement")

simu = Simu(mesh, materiau)

# # Affichage etc
# fig, ax = Affichage.Plot_Maillage(simu, deformation=True)
# Affichage.Plot_NoeudsMaillage(simu, ax, noeuds_en_0, c='red')
# Affichage.Plot_NoeudsMaillage(simu, ax, noeuds_en_L, c='blue', showId=True)
# Affichage.Plot_Maillage(simu, deformation=True)
# Affichage.Plot_NoeudsMaillage(simu, showId=True)

# Renseigne les condtions limites

# Affichage.Plot_NoeudsMaillage(simu.mesh, showId=True)
# plt.show()

# simu.Add_Bc_Dirichlet("displacement", noeuds_en_0, ["x","y"], 0.0, "Encastrement")

simu.add_lineLoad("displacement",noeuds_en_L, ["y"], [-lineLoad])

simu.Condition_Neumann(noeuds_en_L, valeur=-P, directions=["y"])
# simu.Condition_Neumann(noeuds_en_L, valeur=P, directions=["y"])


# Assemblage du système matricielle
simu.Assemblage_u()

simu.Solve_u(resolution=2, useCholesky=False)


# Post traitement --------------------------------------------------------------------------------------
Affichage.NouvelleSection("Post traitement")

simu.Resume()


if saveParaview:
        filename = Dossier.NewFile("Etude2D\\solution2D", results=True)
        PostTraitement.SaveParaview(simu, filename)

if plotResult:

        tic = TicTac()
        
        fig, ax = Affichage.Plot_Maillage(simu, deformation=True)
        # plt.savefig(Dossier.NewFile("Etude2D\\maillage2D.png",results=True))
        # Affichage.Plot_NoeudsMaillage(simu, showId=True)
        Affichage.Plot_Result(simu, "dy", deformation=True, valeursAuxNoeuds=True)
        # plt.savefig(Dossier.NewFile("Etude2D\\dy.png",results=True))
        Affichage.Plot_Result(simu, "Svm", deformation=True, valeursAuxNoeuds=True)
        # plt.savefig(Dossier.NewFile("Etude2D\\Svm_n.png",results=True))
        Affichage.Plot_Result(simu, "Svm", deformation=True, valeursAuxNoeuds=False, affichageMaillage=False)
        # plt.savefig(Dossier.NewFile("Etude2D\\Svm_e.png",results=True))
        
        
        tic.Tac("Post Traitement","Affichage des figures", plotResult)

ticTot.Tac("Temps script","Temps total", True)        

TicTac.getResume()        

if plotResult:
        plt.show()

# %%
