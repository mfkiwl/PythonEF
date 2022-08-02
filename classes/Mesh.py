
from typing import cast
import numpy as np
from pandas import array
import scipy.sparse as sp

from Geom import *
from GroupElem import GroupElem
from TicTac import TicTac

class Mesh:

    def __init__(self, dict_groupElem: dict, verbosity=True):
        """Création du maillage depuis coordo et connection
        Le maillage est l'entité qui possède les groupes d'élements
        
        affichageMaillage : bool, optional
            Affichage après la construction du maillage, by default True
        """

        # Onrevifie que l'on contient que des GroupElem
        for item in dict_groupElem.values():
            assert isinstance(item, GroupElem)

        self.__dim = int(np.max([k for k in dict_groupElem.keys()]))

        self.__dict_groupElem = dict_groupElem

        self.__dict_B_dep_e_pg = {}

        self.__verbosity = verbosity
        """le maillage peut ecrire dans la console"""
        
        if self.__verbosity:
            self.Resume()            
    
    def Resume(self):
        print(f"\nType d'elements: {self.elemType}")
        print(f"Ne = {self.Ne}, Nn = {self.Nn}, nbDdl = {self.Nn*self.__dim}")
    
    def get_groupElem(self, dim=None):
        if dim != None:
            return cast(GroupElem, self.__dict_groupElem[dim])
        else:
            return cast(GroupElem, self.__dict_groupElem[self.__dim])
    groupElem = cast(GroupElem, property(get_groupElem))   

    def Get_Nodes_Conditions(self, conditionX=True, conditionY=True, conditionZ=True):
        """Renvoie la liste de noeuds qui respectent les condtions

        Args:
            conditionX (bool, optional): Conditions suivant x. Defaults to True.
            conditionY (bool, optional): Conditions suivant y. Defaults to True.
            conditionZ (bool, optional): Conditions suivant z. Defaults to True.

        Exemples de contitions:
            x ou toto ça n'a pas d'importance
            condition = lambda x: x < 40 and x > 20
            condition = lambda x: x == 40
            condition = lambda x: x >= 0

        Returns:
            list(int): lite des noeuds qui respectent les conditions
        """
        return self.groupElem.Get_Nodes_Conditions(conditionX, conditionY, conditionZ)
    
    def Get_Nodes_Point(self, point: Point):
        """Renvoie la liste le noeud sur le point"""
        return self.groupElem.Get_Nodes_Point(point)

    def Get_Nodes_Line(self, line: Line):
        """Renvoie la liste de noeuds qui sont sur la ligne"""
        return self.groupElem.Get_Nodes_Line(line)

    def Get_Nodes_Domain(self, domain: Domain):
        """Renvoie la liste de noeuds qui sont dans le domaine"""
        return self.groupElem.Get_Nodes_Domain(domain)
    
    def Get_Nodes_Circle(self, circle: Circle):
        """Renvoie la liste de noeuds qui sont dans le cercle"""
        return self.groupElem.Get_Nodes_Circle(circle)

    def Localises_sol_e(self, sol: np.ndarray):
        """sur chaque elements on récupère les valeurs de sol"""
        return cast(np.ndarray, self.groupElem.Localise_sol_e(sol))
        
    def __get_Ne(self, dim=None):
        if isinstance(dim,int):
            return cast(GroupElem, self.groupElem(dim)).Ne 
        else:
            return self.groupElem.Ne
    Ne = property(__get_Ne)
    """Nombre d'élements du maillage"""
    
    def __get_Nn(self, dim=None):        
        if isinstance(dim,int):
            return cast(GroupElem, self.groupElem(dim)).Nn 
        else:
            return self.groupElem.Nn
    Nn = property(__get_Nn)
    """Nombre de noeuds du maillage"""

    def __get_nPe(self, dim=None):
        if isinstance(dim,int):
            return cast(GroupElem, self.groupElem(dim)).nPe
        else:
            return self.groupElem.nPe
    nPe = property(__get_nPe)
    """noeuds par element"""

    def __get_dim(self):
        return self.__dim
    dim = property(__get_dim)
    """Dimension du maillage"""

    def __get_coordo(self, dim=None):
        if isinstance(dim, int):
            return cast(GroupElem, self.groupElem(dim)).coordo
        else:
            return self.groupElem.coordo
    coordo = cast(np.ndarray, property(__get_coordo))
    """matrice des coordonnées de noeuds (Nn,3)"""

    def __get_nodes(self, dim=None):
        if isinstance(dim, int):
            return cast(GroupElem, self.groupElem(dim)).nodes
        else:
            return self.groupElem.nodes
    nodes = cast(np.ndarray, property(__get_nodes))
    """numéros des noeuds du maillage"""

    def __get_coordoGlob(self, dim=None):
        if isinstance(dim, int):
            return cast(GroupElem, self.groupElem(dim)).coordoGlob
        else:
            return self.groupElem.coordoGlob
    coordoGlob = cast(np.ndarray, property(__get_coordoGlob))
    """matrice de coordonnées globale du maillage (maillage.Nn, 3)"""

    def __get_connect(self, dim=None):
        if isinstance(dim, int):
            return cast(GroupElem, self.groupElem(dim)).connect
        else:
            return self.groupElem.connect        
    connect = cast(np.ndarray, property(__get_connect))
    """connection des elements (Ne, nPe)"""
    
    def __get_connect_n_e(self):
        return self.groupElem.connect_n_e
    connect_n_e = cast(sp.csr_matrix, property(__get_connect_n_e))
    """matrices de 0 et 1 avec les 1 lorsque le noeud possède l'element (Nn, Ne)\n
        tel que : valeurs_n(Nn,1) = connect_n_e(Nn,Ne) * valeurs_e(Ne,1)"""

    def __get_assembly(self):
        return self.groupElem.assembly_e
    assembly_e = cast(np.ndarray, property(__get_assembly))
    """matrice d'assemblage (Ne, nPe*dim)"""

    def __get_lignesVector_e(self):
        return np.repeat(self.assembly_e, self.nPe*self.__dim).reshape((self.Ne,-1))
    lignesVector_e = cast(np.ndarray, property(__get_lignesVector_e))
    """lignes pour remplir la matrice d'assemblage en vecteur (déplacement)"""

    def __get_colonnesVector_e(self):
        return np.repeat(self.assembly_e, self.nPe*self.__dim, axis=0).reshape((self.Ne,-1))
    colonnesVector_e = cast(np.ndarray, property(__get_colonnesVector_e))
    """colonnes pour remplir la matrice d'assemblage en vecteur (déplacement)"""

    def __get_lignesScalar_e(self):
        return np.repeat(self.connect, self.nPe).reshape((self.Ne,-1))         
    lignesScalar_e = cast(np.ndarray, property(__get_lignesScalar_e))
    """lignes pour remplir la matrice d'assemblage en scalaire (endommagement, ou thermique)"""

    def __get_colonnesScalar_e(self):
        return np.repeat(self.connect, self.nPe, axis=0).reshape((self.Ne,-1))
    colonnesScalar_e = cast(np.ndarray, property(__get_colonnesScalar_e))
    """colonnes pour remplir la matrice d'assemblage en scalaire (endommagement, ou thermique)"""

    def get_nPg(self, matriceType: str):
        """nombre de point d'intégration par élement"""
        return self.groupElem.get_gauss(matriceType).nPg

    def get_poid_pg(self, matriceType: str):
        """Points d'intégration (pg, dim, poid)"""
        return self.groupElem.get_gauss(matriceType).poids

    def get_jacobien_e_pg(self, matriceType: str):
        """jacobien (e, pg)"""
        return self.groupElem.get_jacobien_e_pg(matriceType)
    
    def get_N_scalaire_pg(self, matriceType: str):
        """Fonctions de formes dans l'element isoparamétrique pour un scalaire (npg, 1, npe)\n
        Matrice des fonctions de forme dans element de référence (ksi, eta)\n
        [N1(ksi,eta) N2(ksi,eta) Nn(ksi,eta)] \n
        """
        return self.groupElem.get_N_pg(matriceType)

    def get_N_vecteur_pg(self, matriceType: str):
        """Fonctions de formes dans l'element de reférences pour un vecteur (npg, dim, npe*dim)\n
        Matrice des fonctions de forme dans element de référence (ksi, eta)\n
        [N1(ksi,eta) 0 N2(ksi,eta) 0 Nn(ksi,eta) 0 \n
        0 N1(ksi,eta) 0 N2(ksi,eta) 0 Nn(ksi,eta)]\n
        """
        return self.groupElem.get_N_pg(matriceType, self.__dim)

    def get_B_sclaire_e_pg(self, matriceType: str):
        """Derivé des fonctions de formes dans la base réele en sclaire\n
        [dN1,x dN2,x dNn,x\n
        dN1,y dN2,y dNn,y]\n        
        (epij)
        """
        return self.groupElem.get_dN_e_pg(matriceType)

    def get_B_dep_e_pg(self, matriceType: str):
        """Derivé des fonctions de formes dans la base réele pour le problème de déplacement (e, pg, (3 ou 6), nPe*dim)\n
        exemple en 2D :\n
        [dN1,x 0 dN2,x 0 dNn,x 0\n
        0 dN1,y 0 dN2,y 0 dNn,y\n
        dN1,y dN1,x dN2,y dN2,x dN3,y dN3,x]\n

        (epij) Dans la base de l'element et en Kelvin Mandel
        """

        return self.groupElem.get_B_dep_e_pg(matriceType)

    def get_leftDepPart(self, matriceType: str):
        """Renvoie la partie qui construit le therme de gauche de déplacement\n
        Ku_e = jacobien_e_pg * poid_pg * B_dep_e_pg' * c_e_pg * B_dep_e_pg\n
        
        Renvoie (epij) -> jacobien_e_pg * poid_pg * B_dep_e_pg'
        """

        return self.groupElem.get_leftDepPart(matriceType)
    
    def get_phaseField_ReactionPart_e_pg(self, matriceType: str):
        """Renvoie la partie qui construit le therme de reaction\n
        K_r_e_pg = jacobien_e_pg * poid_pg * r_e_pg * Nd_pg' * Nd_pg\n
        
        Renvoie (epij) -> jacobien_e_pg * poid_pg * Nd_pg' * Nd_pg
        """

        return self.groupElem.get_phaseField_ReactionPart_e_pg(matriceType)

    def get_phaseField_DiffusePart_e_pg(self, matriceType: str):
        """Renvoie la partie qui construit le therme de diffusion\n
        DiffusePart_e_pg = jacobien_e_pg * poid_pg * k * Bd_e_pg' * Bd_e_pg\n
        
        Renvoie -> jacobien_e_pg * poid_pg * Bd_e_pg' * Bd_e_pg
        """

        return self.groupElem.get_phaseField_DiffusePart_e_pg(matriceType)

    def get_phaseField_SourcePart_e_pg(self, matriceType: str):
        """Renvoie la partie qui construit le therme de source\n
        SourcePart_e_pg = jacobien_e_pg, poid_pg, f_e_pg, Nd_pg'\n
        
        Renvoie -> jacobien_e_pg, poid_pg, Nd_pg'
        """

        return self.groupElem.get_phaseField_SourcePart_e_pg(matriceType)
    
    def get_nbFaces(self):
        return self.groupElem.nbFaces
    
    def __get_elemenType(self):
        return self.groupElem.elemType
    elemType = cast(str, property(__get_elemenType))

    def get_connectTriangle(self):
        """Transforme la matrice de connectivité pour la passer dans le trisurf en 2D"""
        return self.groupElem.get_connectTriangle()
    
    def get_connect_Faces(self):
        """Récupère les faces de chaque element
        """
        return self.groupElem.get_connect_Faces()
        

        