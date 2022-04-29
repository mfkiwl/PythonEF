from typing import cast
import numpy as np
import scipy.sparse as sp

from Element import ElementIsoparametrique
from TicTac import TicTac

class Mesh:   
    

    def __init__(self, dim: int, coordo: np.ndarray, connect: np.ndarray, verbosity=True):
        """Création du maillage depuis coordo et connection

        Parameters
        ----------
        coordo : list
            Coordonnées des noeuds dim(Nn,3), by default []
        connection : list
            Matrice de connection dim(Ne,nPe), by default []
        affichageMaillage : bool, optional
            Affichage après la construction du maillage, by default True
        """
    
        # Vérfication
        assert isinstance(coordo, np.ndarray) and isinstance(coordo[0], np.ndarray),"Doit fournir une liste de ndarray de ndarray !"
        
        assert isinstance(connect, np.ndarray) and isinstance(connect[0], np.ndarray),"Doit fournir une liste de liste"

        self.__dim = dim
        """dimension du maillage"""

        self.__verbosity = verbosity
        """le maillage peut ecrire dans la console"""

        self.__coordo = np.array(coordo)
        """matrice des coordonnées de noeuds (Nn,3)"""
        self.__connect = np.array(connect)
        """connection des elements (Ne, nPe)"""

        self.__elementIsoParametrique = ElementIsoparametrique(dim, connect.shape[1], verbosity)
        """Element utilisé dans le maillage"""

        # Matrices pour affichage des résultats
        
        if verbosity:
            print(f"\nType d'elements: {self.elemType}")
            print(f"Ne = {self.Ne}, Nn = {self.Nn}, nbDdl = {self.Nn*self.__dim}") 
    
    def Get_Nodes(self, conditionX=True, conditionY=True, conditionZ=True):
        """Renvoie la liste de noeuds qui respectent la les condtions

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

        verifX = isinstance(conditionX, bool)
        verifY = isinstance(conditionY, bool)
        verifZ = isinstance(conditionZ, bool)

        listNoeud = list(range(self.Nn))
        if verifX and verifY and verifZ:
            return listNoeud

        coordoX = self.__coordo[:,0]
        coordoY = self.__coordo[:,1]
        coordoZ = self.__coordo[:,2]
        
        arrayVrai = np.array([True]*self.Nn)
        
        # Verification suivant X
        if verifX:
            valideConditionX = arrayVrai
        else:
            try:
                valideConditionX = conditionX(coordoX)
            except:
                valideConditionX = [conditionX(coordoX[n]) for n in listNoeud]

        # Verification suivant Y
        if verifY:
            valideConditionY = arrayVrai
        else:
            try:
                valideConditionY = conditionY(coordoY)
            except:
                valideConditionY = [conditionY(coordoY[n]) for n in listNoeud]
        
        # Verification suivant Z
        if verifZ:
            valideConditionZ = arrayVrai
        else:
            try:
                valideConditionZ = conditionZ(coordoZ)
            except:
                valideConditionZ = [conditionZ(coordoZ[n]) for n in listNoeud]
        
        conditionsTotal = valideConditionX * valideConditionY * valideConditionZ

        noeuds = list(np.where(conditionsTotal)[0])
        
        return noeuds

    def Localise_e(self, sol: np.ndarray):
        """localise les valeurs de noeuds sur les elements"""
        tailleVecteur = self.Nn * self.__dim

        if sol.shape[0] == tailleVecteur:
            sol_e = sol[self.assembly_e]
        else:
            sol_e = sol[self.__connect]
        
        return sol_e    
        
    def __get_Ne(self):
        return int(len(self.__connect))
    Ne = property(__get_Ne)
    """Nombre d'élements du maillage"""
    
    def __get_Nn(self):        
        return int(len(self.__coordo))
    Nn = property(__get_Nn)
    """Nombre de noeuds du maillage"""

    def __get_nPe(self):
        return self.__elementIsoParametrique.nPe
    nPe = property(__get_nPe)
    """noeuds par element"""

    def __get_dim(self):
        return self.__dim
    dim = property(__get_dim)
    """Dimension du maillage"""

    def __get_coordo(self):
        return self.__coordo.copy()
    coordo = cast(np.ndarray, property(__get_coordo))
    """matrice des coordonnées de noeuds (Nn,3)"""

    def __get_connect(self):
        return self.__connect.copy()
    connect = cast(np.ndarray, property(__get_connect))
    """connection des elements (Ne, nPe)"""
    
    def __get_connect_n_e(self):
        # Ici l'objectif est de construire une matrice qui lorsque quon va la multiplier a un vecteur valeurs_e de taille ( Ne x 1 ) va donner
        # valeurs_n_e(Nn,1) = connecNoeud(Nn,Ne) valeurs_n_e(Ne,1)
        # ou connecNoeud(Nn,:) est un vecteur ligne composé de 0 et de 1 qui permetra de sommer valeurs_e[noeuds]
        # Ensuite, il suffit juste par divisier par le nombre de fois que le noeud apparait dans la ligne        
        # L'idéal serait dobtenir connectNoeud (Nn x nombre utilisation du noeud par element) rapidement
        
        Nn = self.Nn
        Ne = self.Ne
        nPe = self.__connect.shape[1]
        listElem = np.arange(Ne)

        lignes = self.__connect.reshape(-1)
        colonnes = np.repeat(listElem, nPe)

        return sp.csr_matrix((np.ones(nPe*Ne),(lignes, colonnes)),shape=(Nn,Ne))
    connect_n_e = cast(sp.csr_matrix, property(__get_connect_n_e))
    """matrices de 0 et 1 avec les 1 lorsque le noeud possède l'element (Nn, Ne)\n
        tel que : valeurs_n(Nn,1) = connect_n_e(Nn,Ne) * valeurs_e(Ne,1)"""

    def __get_assembly(self):
        nPe = self.__elementIsoParametrique.nPe
        dim = self.__dim
        taille = nPe*dim

        assembly = np.zeros((self.Ne, nPe*dim), dtype=np.int64)
        assembly[:, np.arange(0, taille, dim)] = np.array(self.connect) * dim
        assembly[:, np.arange(1, taille, dim)] = np.array(self.connect) * dim + 1
        if dim == 3:
            assembly[:, np.arange(2, taille, dim)] = np.array(self.connect) * dim + 2

        return assembly
    assembly_e = cast(np.ndarray, property(__get_assembly))
    """matrice d'assemblage (Ne, nPe*dim)"""

    def __get_lignesVector_e(self):
        return np.repeat(self.assembly_e, self.__elementIsoParametrique.nPe*self.__dim).reshape((self.Ne,-1))
    lignesVector_e = cast(np.ndarray, property(__get_lignesVector_e))
    """lignes pour remplir la matrice d'assemblage en vecteur (déplacement)"""

    def __get_colonnesVector_e(self):
        return np.repeat(self.assembly_e, self.__elementIsoParametrique.nPe*self.__dim, axis=0).reshape((self.Ne,-1))
    colonnesVector_e = cast(np.ndarray, property(__get_colonnesVector_e))
    """colonnes pour remplir la matrice d'assemblage en vecteur (déplacement)"""

    def __get_lignesScalar_e(self):
        return np.repeat(self.connect, self.__elementIsoParametrique.nPe).reshape((self.Ne,-1))         
    lignesScalar_e = cast(np.ndarray, property(__get_lignesScalar_e))
    """lignes pour remplir la matrice d'assemblage en scalaire (endommagement, ou thermique)"""

    def __get_colonnesScalar_e(self):
        return np.repeat(self.connect, self.__elementIsoParametrique.nPe, axis=0).reshape((self.Ne,-1))
    colonnesScalar_e = cast(np.ndarray, property(__get_colonnesScalar_e))
    """colonnes pour remplir la matrice d'assemblage en scalaire (endommagement, ou thermique)"""

    def get_nPg(self, matriceType: str):
        """nombre de point d'intégration par élement"""
        return self.__elementIsoParametrique.get_nPg(matriceType)

    def get_poid_pg(self, matriceType: str):
        """Points d'intégration (pg, dim, poid)"""
        return self.__elementIsoParametrique.get_poid_pg(matriceType)

    def get_jacobien_e_pg(self, matriceType: str):
        """jacobien (e, pg)"""
        nodes_e = self.__get_nodes_e()
        return self.__elementIsoParametrique.get_jacobien_e_pg(nodes_e, matriceType)

    def __get_nodes_e(self):
        nodes_n = self.__coordo[:, range(self.__dim)]
        nodes_e = nodes_n[self.connect]
        return nodes_e
    
    def get_dN(self, matriceType: str):
        assert matriceType in ElementIsoparametrique.get_MatriceType()
        nodes_e = self.__get_nodes_e()
        dN_e_pg = self.__elementIsoParametrique.__get_dN_e_pg(nodes_e, matriceType)
        return dN_e_pg
    
    def get_N_scalaire_pg(self, matriceType: str):
        """Fonctions de formes dans l'element isoparamétrique pour un scalaire (npg, 1, npe)
        Matrice des fonctions de forme dans element de référence (ksi, eta)\n
        [N1(ksi,eta) N2(ksi,eta) Nn(ksi,eta)] \n
        """
        return self.__elementIsoParametrique.get_N_scalaire_pg(matriceType)

    def get_N_vecteur_pg(self, matriceType: str):
        """Fonctions de formes dans l'element isoparamétrique pour un vecteur (npg, dim, npe*dim)
        Matrice des fonctions de forme dans element de référence (ksi, eta)\n
        [N1(ksi,eta) 0 N2(ksi,eta) 0 Nn(ksi,eta) 0 \n
        0 N1(ksi,eta) 0 N2(ksi,eta) 0 Nn(ksi,eta)]"""
        return self.__elementIsoParametrique.get_N_vecteur_pg(matriceType)

    def get_B_sclaire_e_pg(self, matriceType: str):
        """Derivé des fonctions de formes dans la base réele en sclaire"""

        nodes_n = self.__coordo[:, range(self.__dim)]
        nodes_e = np.array(nodes_n[self.__connect])

        return self.__elementIsoParametrique.get_dN_e_pg(nodes_e, matriceType)

    def get_B_dep_e_pg(self, matriceType: str):
        """Derivé des fonctions de formes dans la base réele pour le problème de déplacement (e, pg, (3 ou 6), nPe*dim)\n
        exemple en 2D :\n
        [dN1,x 0 dN2,x 0 dNn,x 0\n
        0 dN1,y 0 dN2,y 0 dNn,y\n
        dN1,y dN1,x dN2,y dN2,x dN3,y dN3,x]
        """
        # get dN_e_pg
        nodes_n = self.__coordo[:, range(self.__dim)]
        nodes_e = np.array(nodes_n[self.__connect])
        dN_e_pg = self.__elementIsoParametrique.get_dN_e_pg(nodes_e, matriceType)

        nPg = self.get_nPg(matriceType)
        nPe = self.__elementIsoParametrique.nPe
        dim = self.__dim
        listnPe = np.arange(nPe)
        
        colonnes0 = np.arange(0, nPe*dim, dim)
        colonnes1 = np.arange(1, nPe*dim, dim)

        if self.__dim == 2:
            B_e_pg = np.array([[np.zeros((3, nPe*dim))]*nPg]*self.Ne)
            """Derivé des fonctions de formes dans la base réele en vecteur \n
            """
            
            dNdx = dN_e_pg[:,:,0,listnPe]
            dNdy = dN_e_pg[:,:,1,listnPe]

            B_e_pg[:,:,0,colonnes0] = dNdx
            B_e_pg[:,:,1,colonnes1] = dNdy
            B_e_pg[:,:,2,colonnes0] = dNdy; B_e_pg[:,:,2,colonnes1] = dNdx
        else:
            B_e_pg = np.array([[np.zeros((6, nPe*dim))]*nPg]*self.Ne)

            dNdx = dN_e_pg[:,:,0,listnPe]
            dNdy = dN_e_pg[:,:,1,listnPe]
            dNdz = dN_e_pg[:,:,2,listnPe]

            colonnes2 = np.arange(2, nPe*dim, dim)

            B_e_pg[:,:,0,colonnes0] = dNdx
            B_e_pg[:,:,1,colonnes1] = dNdy
            B_e_pg[:,:,2,colonnes2] = dNdz
            B_e_pg[:,:,3,colonnes1] = dNdz; B_e_pg[:,:,3,colonnes2] = dNdy
            B_e_pg[:,:,4,colonnes0] = dNdz; B_e_pg[:,:,4,colonnes2] = dNdx
            B_e_pg[:,:,5,colonnes0] = dNdy; B_e_pg[:,:,5,colonnes1] = dNdx

        return B_e_pg    
    

    def get_nbFaces(self):
        if self.__dim == 2:
            return 1
        else:
            # TETRA4
            if self.__connect.shape[1] == 4:
                return 4
    
    def __get_elemenType(self):
        return self.__elementIsoParametrique.type
    elemType = cast(str, property(__get_elemenType))

    def get_connectTriangle(self):
        """Transforme la matrice de connectivité pour la passer dans le trisurf en 2D
        ou construit les faces pour la 3D
        Par exemple pour un quadrangle on construit deux triangles
        pour un triangle à 6 noeuds on construit 4 triangles
        POur la 3D on construit des faces pour passer en Poly3DCollection
        """

        match self.elemType:
            case "TRI3":
                return self.__connect[:,[0,1,2]]
            case "TRI6":
                return np.array(self.__connect[:, [0,3,5,3,1,4,5,4,2,3,4,5]]).reshape(-1,3)
            case "QUAD4":
                return np.array(self.__connect[:, [0,1,3,1,2,3]]).reshape(-1,3)
            case "QUAD8":
                return np.array(self.__connect[:, [4,5,7,5,6,7,0,4,7,4,1,5,5,2,6,6,3,7]]).reshape(-1,3)
    
    def get_connect_Faces(self):
        """Construit les faces pour chaque element

        consruit les identifiants des noeud constuisant les faces

        Returns
        -------
        list de list
            Renvoie une liste de face
        """
        nPe = self.nPe
        match self.elemType:
            case "TRI3":
                return self.__connect[:, [0,1,2,0]]
            case "TRI6":
                return self.__connect[:, [0,3,1,4,2,5,0]]
            case "QUAD4":
                return self.__connect[:, [0,1,2,3,0]]
            case "QUAD8":
                return self.__connect[:, [0,4,1,5,2,6,3,7,0]]
            case "TETRA4":
                # Ici par elexemple on va creer 3 faces, chaque face est composé des identifiants des noeuds
                return np.array(self.__connect[:, [0,1,2,0,1,3,0,2,3,1,2,3]]).reshape(self.Ne*nPe,-1)

# TEST ==============================

import unittest
import os

class Test_Mesh(unittest.TestCase):
    
    def setUp(self):
        
        from Interface_Gmsh import Interface_Gmsh

        list_mesh = []

        for e, element in enumerate(ElementIsoparametrique.get_Types2D()):
            modelGmsh = Interface_Gmsh(2, organisationMaillage=True, typeElement=e, tailleElement=1, verbosity=False)
            (coordo, connect) = modelGmsh.ConstructionRectangle(1, 1)
            mesh = Mesh(2, coordo, connect, verbosity=False)
            list_mesh.append(mesh)

        self.list_Mesh2D = list_mesh

    def test_BienCree(self):

        for mesh in self.list_Mesh2D:
            self.assertIsInstance(mesh, Mesh)

    def test_ConstructionMatrices(self):
        for mesh in self.list_Mesh2D:
            self.__VerficiationConstructionMatrices(mesh)

    # Verifivation
    def __VerficiationConstructionMatrices(self, mesh: Mesh):

        dim = mesh.dim
        connect = mesh.connect
        listElement = range(mesh.Ne)
        listPg = np.arange(mesh.get_nPg("rigi"))
        nPe = connect.shape[1]

        # Verification assemblage
        assembly_e_test = np.array([[int(n * dim + d)for n in connect[e] for d in range(dim)] for e in listElement])
        testAssembly = np.testing.assert_array_almost_equal(mesh.assembly_e, assembly_e_test, verbose=False)
        self.assertIsNone(testAssembly)

        # Verification lignes_e 
        lignes_e_test = np.array([[i for i in mesh.assembly_e[e] for j in mesh.assembly_e[e]] for e in listElement])
        testLignes = np.testing.assert_array_almost_equal(lignes_e_test, mesh.lignesVector_e, verbose=False)
        self.assertIsNone(testLignes)

        # Verification lignes_e 
        colonnes_e_test = np.array([[j for i in mesh.assembly_e[e] for j in mesh.assembly_e[e]] for e in listElement])
        testColonnes = np.testing.assert_array_almost_equal(colonnes_e_test, mesh.colonnesVector_e, verbose=False)
        self.assertIsNone(testColonnes)

        list_B_rigi_e_pg = []

        for e in listElement:
            list_B_rigi_pg = []
            for pg in listPg:
                if dim == 2:
                    B_dep_pg = np.zeros((3, nPe*dim))
                    colonne = 0
                    B_sclaire_e_pg = mesh.get_B_sclaire_e_pg("rigi")
                    dN = B_sclaire_e_pg[e,pg]
                    for n in range(nPe):
                        dNdx = dN[0, n]
                        dNdy = dN[1, n]
                        
                        # B rigi
                        B_dep_pg[0, colonne] = dNdx
                        B_dep_pg[1, colonne+1] = dNdy
                        B_dep_pg[2, colonne] = dNdy; B_dep_pg[2, colonne+1] = dNdx
                        
                        colonne += 2
                    list_B_rigi_pg.append(B_dep_pg)    
                else:
                    B_dep_pg = np.zeros((6, nPe*dim))
                    
                    colonne = 0
                    for n in range(nPe):
                        dNdx = dN[0, n]
                        dNdy = dN[1, n]
                        dNdz = dN[2, n]                        
                        
                        B_dep_pg[0, colonne] = dNdx
                        B_dep_pg[1, colonne+1] = dNdy
                        B_dep_pg[2, colonne+2] = dNdz
                        B_dep_pg[3, colonne] = dNdy; B_dep_pg[3, colonne+1] = dNdx
                        B_dep_pg[4, colonne+1] = dNdz; B_dep_pg[4, colonne+2] = dNdy
                        B_dep_pg[5, colonne] = dNdz; B_dep_pg[5, colonne+2] = dNdx
                        colonne += 3
                    list_B_rigi_pg.append(B_dep_pg)
                    
                
            list_B_rigi_e_pg.append(list_B_rigi_pg)

        B_rigi_e_pg = mesh.get_B_dep_e_pg("rigi")

        testB_rigi = np.testing.assert_array_almost_equal(np.array(list_B_rigi_e_pg), B_rigi_e_pg, verbose=False)
        self.assertIsNone(testB_rigi)

            


if __name__ == '__main__':        
    try:
        os.system("cls")
        unittest.main(verbosity=2)
    except:
        print("")        