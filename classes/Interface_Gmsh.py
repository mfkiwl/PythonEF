from typing import cast
import gmsh
import sys
import numpy as np

from GroupElem import GroupElem
from Element import ElementIsoparametrique
from TicTac import TicTac
from Affichage import Affichage
import matplotlib.pyplot as plt

class Interface_Gmsh:        

        def __init__(self, affichageGmsh=False, gmshVerbosity=False, verbosity=True):                
                
                self.__affichageGmsh = affichageGmsh
                """affichage du maillage sur gmsh"""
                self.__gmshVerbosity = gmshVerbosity
                """gmsh peut ecrire dans la console"""
                self.__verbosity = verbosity
                """modelGmsh peut ecrire dans la console"""

                if verbosity:
                        Affichage.NouvelleSection("Gmsh")

        def __initGmsh(self):
                gmsh.initialize()
                if self.__gmshVerbosity == False:
                        gmsh.option.setNumber('General.Verbosity', 0)
                gmsh.model.add("model")
        
        def __CheckType(self, dim: int, elemType: str):
                if dim == 2:
                        assert elemType in ElementIsoparametrique.get_Types2D()                        
                elif dim == 3:
                        assert elemType in ElementIsoparametrique.get_Types3D()

        def Importation3D(self,fichier="", elemType="TETRA4", tailleElement=0.0):
                """Importe depuis un 3D

                elemTypes = ["TETRA4"]
                
                Returns:
                    tuple: coordo, connect
                """

                self.__initGmsh()

                assert tailleElement >= 0.0, "Doit être supérieur ou égale à 0"
                self.__tailleElement3D = tailleElement
                self.__CheckType(3, elemType)
                
                tic = TicTac()

                # Importation du fichier
                gmsh.model.occ.importShapes(fichier)

                tic.Tac("Mesh","Importation du fichier step", self.__verbosity)

                self.__ConstructionMaillageGmsh(3, elemType)

                return self.__ConstructionCoordoConnect(3)

        def ConstructionRectangle(self, largeur: float, hauteur: float,
        elemType="TRI3", tailleElement=0.0, isOrganised=False):

                """Construit un rectangle

                elemTypes = ["TRI3", "TRI6", "QUAD4", "QUAD8"]
                
                Returns:
                    tuple: coordo, connect
                """

                self.__initGmsh()
                
                assert tailleElement >= 0.0, "Doit être supérieur ou égale à 0"
                self.__CheckType(2, elemType)

                tic = TicTac()

                # Créer les points
                p1 = gmsh.model.geo.addPoint(0, 0, 0, tailleElement)
                p2 = gmsh.model.geo.addPoint(largeur, 0, 0, tailleElement)
                p3 = gmsh.model.geo.addPoint(largeur, hauteur, 0, tailleElement)
                p4 = gmsh.model.geo.addPoint(0, hauteur, 0, tailleElement)

                # Créer les lignes reliants les points
                l1 = gmsh.model.geo.addLine(p1, p2)
                l2 = gmsh.model.geo.addLine(p2, p3)
                l3 = gmsh.model.geo.addLine(p3, p4)
                l4 = gmsh.model.geo.addLine(p4, p1)

                # Créer une boucle fermée reliant les lignes     
                boucle = gmsh.model.geo.addCurveLoop([l1, l2, l3, l4])

                # Créer une surface
                surface = gmsh.model.geo.addPlaneSurface([boucle])
                
                tic.Tac("Mesh","Construction Rectangle", self.__verbosity)
                
                self.__ConstructionMaillageGmsh(2, elemType, surface=surface, isOrganised=isOrganised)
                
                return self.__ConstructionCoordoConnect(2)

        def ConstructionRectangleAvecFissure(self, largeur: float, hauteur: float,
        elemType="TRI3", elementSize=0.0, openCrack=False, isOrganised=False):

                """Construit un rectangle avec une fissure ouverte ou non

                elemTypes = ["TRI3", "TRI6", "QUAD4", "QUAD8"]
                
                Returns:
                    tuple: coordo, connect
                """

                self.__initGmsh()
                
                assert elementSize >= 0.0, "Must be greater than or equal to 0"
                self.__CheckType(2, elemType)
                
                tic = TicTac()               

                # Create the points of the rectangle
                p1 = gmsh.model.occ.addPoint(0, 0, 0, elementSize)
                p2 = gmsh.model.occ.addPoint(largeur, 0, 0, elementSize)
                p3 = gmsh.model.occ.addPoint(largeur, hauteur, 0, elementSize)
                p4 = gmsh.model.occ.addPoint(0, hauteur, 0, elementSize)

                # Create the crack points
                p5 = gmsh.model.occ.addPoint(0, hauteur/2, 0, elementSize)
                p6 = gmsh.model.occ.addPoint(largeur/2, hauteur/2, 0, elementSize)

                # Create the lines connecting the points for the surface
                l1 = gmsh.model.occ.addLine(p1, p2)
                l2 = gmsh.model.occ.addLine(p2, p3)
                l3 = gmsh.model.occ.addLine(p3, p4)
                l4 = gmsh.model.occ.addLine(p4, p5)
                l5 = gmsh.model.occ.addLine(p5, p1)

                # Create a closed loop connecting the lines for the surface
                loop = gmsh.model.occ.addCurveLoop([l1, l2, l3, l4, l5])

                # Create a surface
                surface = gmsh.model.occ.addPlaneSurface([loop])
                
                # Create the crack line
                line = gmsh.model.occ.addLine(p5, p6)
                
                gmsh.model.occ.synchronize()

                # Adds the line to the surface
                gmsh.model.mesh.embed(1, [line], 2, surface)

                if openCrack:
                        point = gmsh.model.addPhysicalGroup(0, [p5])
                        crack = gmsh.model.addPhysicalGroup(1, [line])
                        surface = gmsh.model.addPhysicalGroup(2, [surface])
                
                tic.Tac("Mesh","Construction Rectangle Fissuré", self.__verbosity)
                
                if openCrack:
                        self.__ConstructionMaillageGmsh(2, elemType, surface=surface, crack=crack, openBoundary=point, isOrganised=isOrganised)
                else:
                        self.__ConstructionMaillageGmsh(2, elemType, surface=surface, isOrganised=isOrganised)
                
                return self.__ConstructionCoordoConnect(2)

        def __ConstructionMaillageGmsh(self, dim: int, elemType: str, isOrganised=False,
        surface=None, crack=None, openBoundary=None):

                tic = TicTac()

                match dim:
                        case 2:
                                # Impose que le maillage soit organisé                        
                                if isOrganised:
                                        gmsh.model.geo.mesh.setTransfiniteSurface(surface)

                                # Synchronisation
                                gmsh.model.geo.synchronize()

                                if elemType in ["QUAD4","QUAD8"]:
                                        gmsh.model.mesh.setRecombine(2, surface)
                                
                                # Génère le maillage
                                gmsh.model.mesh.generate(2)

                                if elemType in ["QUAD8"]:
                                        gmsh.option.setNumber('Mesh.SecondOrderIncomplete', 1)

                                if elemType in ["TRI3","QUAD4"]:
                                        gmsh.model.mesh.set_order(1)
                                elif elemType in ["TRI6","QUAD8"]:
                                        gmsh.model.mesh.set_order(2)

                                if crack != None:
                                        gmsh.plugin.setNumber("Crack", "Dimension", dim-1)
                                        gmsh.plugin.setNumber("Crack", "PhysicalGroup", crack)
                                        gmsh.plugin.setNumber("Crack", "OpenBoundaryPhysicalGroup", openBoundary)
                                        # gmsh.plugin.setNumber("Crack", "NormalX", 0)
                                        # gmsh.plugin.setNumber("Crack", "NormalY", 0)
                                        # gmsh.plugin.setNumber("Crack", "NormalZ", 1)
                                        gmsh.plugin.run("Crack")
                                        # gmsh.write("meshhh.msh")
                                        # self.__initGmsh()
                                        # gmsh.open("meshhh.msh")
                        
                        case 3:
                                gmsh.model.occ.synchronize()

                                gmsh.option.setNumber("Mesh.MeshSizeMin", self.__tailleElement3D)
                                gmsh.option.setNumber("Mesh.MeshSizeMax", self.__tailleElement3D)
                                gmsh.model.mesh.generate(3)
                
                # Ouvre l'interface de gmsh si necessaire
                if '-nopopup' not in sys.argv and self.__affichageGmsh:
                        gmsh.fltk.run()   
                
                tic.Tac("Mesh","Construction du maillage gmsh", self.__verbosity)

        def __ConstructionCoordoConnect(self, dim: int):
                """construit connect et coordo pour l'importation du maillage"""
                
                tic = TicTac()

                physicalGroups = gmsh.model.getPhysicalGroups()
                entities = gmsh.model.getEntities()

                elementTypes, elementTags, nodeTags = gmsh.model.mesh.getElements()
                nodes, coord, parametricCoord = gmsh.model.mesh.getNodes()

                # Redimensionne sous la forme d'un tableau
                coordo = coord.reshape(-1,3)

                # Construit les elements
                listGmshElem = {}
                for t, gmshId in enumerate(elementTypes):

                        gmshElem = GroupElem(gmshId, elementTags[t]-1, nodeTags[t]-1, coordo)
                        listGmshElem[gmshElem.dim] = gmshElem

                gmshElem = cast(GroupElem, listGmshElem[dim])

                connect = gmshElem.connect
                coordo = gmshElem.coordo                

                gmsh.finalize()

                tic.Tac("Mesh","Récupération du maillage gmsh", self.__verbosity)

                return coordo, connect


# TEST ==============================

import unittest
import os

class Test_ModelGmsh(unittest.TestCase):
        def setUp(self):
                pass
        
        def test_Construction2D(self):

                from Mesh import Mesh
                
                dim = 2

                L = 10
                taille = L/3

                interfaceGmsh = Interface_Gmsh(verbosity=False)

                # Pour chaque type d'element 2D
                for t, elemType in enumerate(ElementIsoparametrique.get_Types2D()):
                        for isOrganised in [True, False]:

                                
                                coordo, connect = interfaceGmsh.ConstructionRectangle(largeur=L, hauteur=L, elemType=elemType, tailleElement=taille, isOrganised=isOrganised)
                                mesh = Mesh(2, coordo=coordo, connect=connect, verbosity=False)

                                Affichage.Plot_NoeudsMaillage(mesh, showId=True)
                                plt.pause(0.00005)
                                
                                interfaceGmsh = Interface_Gmsh(verbosity=False)
                                coordo2, connect2 = interfaceGmsh.ConstructionRectangleAvecFissure(largeur=L, hauteur=L, elemType=elemType, elementSize=taille, isOrganised=isOrganised)
                                mesh2 = Mesh(2, coordo=coordo2, connect=connect2, verbosity=False)

                                Affichage.Plot_NoeudsMaillage(mesh2, showId=True)
                                plt.pause(0.00005)

                                # Affiche le maillage

                pass

        
        def test_Importation3D(self):

                import Dossier
                from Mesh import Mesh
                
                # Pour chaque type d'element 3D
                for t, elemType in enumerate(ElementIsoparametrique.get_Types3D()):
                        interfaceGmsh = Interface_Gmsh(verbosity=False)
                        path = Dossier.GetPath()
                        fichier = path + "\\models\\part.stp" 
                        coordo, connect = interfaceGmsh.Importation3D(fichier, elemType=elemType, tailleElement=120)
                        mesh = Mesh(3, coordo, connect, verbosity=False)
                        Affichage.Plot_NoeudsMaillage(mesh, showId=True)
                        plt.pause(0.00005)

    
           
if __name__ == '__main__':        
    try:
        os.system("cls")
        unittest.main(verbosity=2)
    except:
        print("")   
                
        
        
        

