
from inspect import stack
from typing import cast

from Geom import *
from Gauss import Gauss
from TicTac import TicTac
from matplotlib import pyplot as plt
import CalcNumba


import numpy as np
import scipy.sparse as sp

class GroupElem:

        def __init__(self, gmshId: int, connect: np.ndarray, elements: np.ndarray,
        coordoGlob: np.ndarray, nodes: np.ndarray,
        verbosity=False):

            self.__gmshId = gmshId            
            
            # Elements
            self.__elements = elements
            self.__connect = connect
            
            # Noeuds
            self.__nodes = nodes
            self.__coordoGlob = coordoGlob
            self.__coordo = cast(np.ndarray, coordoGlob[nodes])

            self.__verbosity = verbosity

            # Dictionnaires pour chaque types de matrices
            if self.dim > 0:
                self.__dict_dN_e_pg = {}
                self.__dict_F_e_pg = {}                
                self.__dict_invF_e_pg = {}                
                self.__dict_jacobien_e_pg = {}   
                self.__dict_B_dep_e_pg = {}
                self.__dict_leftDepPart = {}
                self.__dict_phaseField_ReactionPart_e_pg = {}
                self.__dict_phaseField_DiffusePart_e_pg = {}
                self.__dict_phaseField_SourcePart_e_pg = {}
        
        ################################################ METHODS ##################################################

        def __get_elemType(self):
            """type d'elements"""
            return GroupElem.Get_ElemInFos(self.__gmshId)[0]
        elemType = cast(str, property(__get_elemType))

        def __get_nPe(self):
            """nombre de noeuds par element"""
            return GroupElem.Get_ElemInFos(self.__gmshId)[1]
        nPe = cast(int, property(__get_nPe))

        def __get_dim(self):
            """Dimension de l'element"""
            return GroupElem.Get_ElemInFos(self.__gmshId)[2]
        dim = cast(int, property(__get_dim))

        def __get_Ne(self):
            """nombre delement"""
            return self.__connect.shape[0]
        Ne = cast(int, property(__get_Ne))

        def __get_nodes(self):
            return self.__nodes.copy()
        nodes = cast(np.ndarray, property(__get_nodes))

        def __get_elements(self):
            return self.__elements.copy()
        elements = cast(np.ndarray, property(__get_elements))

        def __get_Nn(self):
            return self.__nodes.shape[0]
            # return self.__nodes.max()
        Nn = property(__get_Nn)

        def __get_connect(self):
            return self.__connect.copy()
        connect = cast(np.ndarray, property(__get_connect))
        """matrice de connection de l'element (Ne, nPe)"""

        def __get_connect_n_e(self):
            # Ici l'objectif est de construire une matrice qui lorsque quon va la multiplier a un vecteur valeurs_e de taille ( Ne x 1 ) va donner
            # valeurs_n_e(Nn,1) = connecNoeud(Nn,Ne) valeurs_n_e(Ne,1)
            # ou connecNoeud(Nn,:) est un vecteur ligne composé de 0 et de 1 qui permetra de sommer valeurs_e[noeuds]
            # Ensuite, il suffit juste par divisier par le nombre de fois que le noeud apparait dans la ligne        
            # L'idéal serait dobtenir connectNoeud (Nn x nombre utilisation du noeud par element) rapidement        
            Ne = self.Ne
            nPe = self.nPe
            listElem = np.arange(Ne)

            lignes = self.connect.reshape(-1)

            Nn = int(lignes.max()+1)
            colonnes = np.repeat(listElem, nPe)

            return sp.csr_matrix((np.ones(nPe*Ne),(lignes, colonnes)),shape=(Nn,Ne))
        connect_n_e = cast(sp.csr_matrix, property(__get_connect_n_e))
        """matrices de 0 et 1 avec les 1 lorsque le noeud possède l'element (Nn, Ne)\n
            tel que : valeurs_n(Nn,1) = connect_n_e(Nn,Ne) * valeurs_e(Ne,1)"""

        def get_elements(self, noeuds: np.ndarray, exclusivement=True):
            "récupérations des élements pour utilise exclusivement ou non les noeuds renseigné"
            connect = self.__connect
            connect_n_e = self.connect_n_e

            lignes, colonnes, valeurs = sp.find(connect_n_e[noeuds])
            elements = np.unique(colonnes)

            if exclusivement:
                listElem = [e for e in elements if not False in [n in noeuds for n in connect[e]]]        
                elements = np.array(listElem)

            return elements

        def get_assembly(self, dim=None):
            nPe = self.nPe
            if dim == None:
                dim = self.dim
            taille = nPe*dim

            assembly = np.zeros((self.Ne, taille), dtype=np.int64)
            connect = self.connect

            for d in range(dim):
                assembly[:, np.arange(d, taille, dim)] = np.array(connect) * dim + d

            return assembly
        assembly_e = cast(np.ndarray, property(get_assembly))
        """matrice d'assemblage (Ne, nPe*dim)"""

        
        

        def __get_coordo(self):
            return self.__coordo
        coordo = cast(np.ndarray, property(__get_coordo))
        """matrice de coordonnées du groupe d'element (Nn, 3)"""

        def __get_coordoGlob(self):
            return self.__coordoGlob
        coordoGlob = cast(np.ndarray, property(__get_coordoGlob))
        """matrice de coordonnées globale du maillage (maillage.Nn, 3)"""

        def __get_nbFaces(self):
            if self.dim in [0,1]:
                return 0
            elif self.dim == 2:
                return 1
            elif self.dim == 3:                
                if self.elemType == "TETRA4":
                    return 4
                elif self.elemType == "HEXA8":
                    return 6
                elif self.elemType == "PRISM6":
                    return 5
                else:
                    raise "Element inconnue"
        nbFaces = cast(int, property(__get_nbFaces))

        def get_gauss(self, matriceType: str):
            return Gauss(self.elemType, matriceType)
        
        def get_coordo_e_p(self, matriceType: str, elements=np.array([])):
            """Renvoie les coordonnées des points de gauss chaque element"""

            N_scalaire = self.get_N_pg(matriceType)

            # récupère les coordonnées des noeuds
            coordo = self.__coordoGlob

            # coordonnées localisées sur l'elements
            if elements.size == 0:
                coordo_e =  coordo[self.__connect]
            else:
                coordo_e =  coordo[self.__connect[elements]]

            # on localise les coordonnées sur les points de gauss
            coordo_e_p = np.einsum('pij,ejn->epn', N_scalaire, coordo_e, optimize='optimal')

            return np.array(coordo_e_p)

        def get_N_pg(self, matriceType: str, repetition=1):
            """Fonctions de formes dans la base de réference

            Args:
                matriceType (str): ["rigi","masse"]
                isScalaire (bool): type de matrice N\n

            Returns:
                np.ndarray: . Fonctions de formes vectorielles (pg, rep=2, rep=2*dim), dans la base (ksi, eta ...)\n
                                [Ni 0 . . . Nn 0 \n
                                0 Ni . . . 0 Nn]

                            . Fonctions de formes scalaires (pg, rep=1, nPe), dans la base (ksi, eta ...)\n
                                [Ni . . . Nn]
            """
            if self.dim == 0: return

            assert isinstance(repetition, int)
            assert repetition >= 1

            N_pg = self.__get_N_pg(matriceType)

            if not isinstance(N_pg, np.ndarray): return

            if repetition <= 1:
                return N_pg
            else:
                taille = N_pg.shape[2]*(repetition)
                N_vect_pg = np.zeros((N_pg.shape[0] ,repetition , taille))

                for r in range(repetition):
                    N_vect_pg[:, r, np.arange(r, taille, repetition)] = N_pg[:,0,:]
                
                return N_vect_pg
        
        def get_dN_e_pg(self, matriceType: str):
            """Derivé des fonctions de formes dans la base réele en sclaire\n
            [dN1,x dN2,x dNn,x\n
            dN1,y dN2,y dNn,y]\n        
            """
            assert matriceType in GroupElem.get_MatriceType()

            if matriceType not in self.__dict_dN_e_pg.keys():

                invF_e_pg = self.get_invF_e_pg(matriceType)

                dN_pg = self.get_dN_pg(matriceType)

                # Derivé des fonctions de formes dans la base réele
                dN_e_pg = np.array(np.einsum('epik,pkj->epij', invF_e_pg, dN_pg, optimize='optimal'))
                self.__dict_dN_e_pg[matriceType] = dN_e_pg

            return cast(np.ndarray, self.__dict_dN_e_pg[matriceType]).copy()

        def get_B_dep_e_pg(self, matriceType: str):
            """Derivé des fonctions de formes dans la base réele pour le problème de déplacement (e, pg, (3 ou 6), nPe*dim)\n
            exemple en 2D :\n
            [dN1,x 0 dN2,x 0 dNn,x 0\n
            0 dN1,y 0 dN2,y 0 dNn,y\n
            dN1,y dN1,x dN2,y dN2,x dN3,y dN3,x]\n

            (epij) Dans la base de l'element et en Kelvin Mandel
            """
            assert matriceType in GroupElem.get_MatriceType()

            if matriceType not in self.__dict_B_dep_e_pg.keys():

                dN_e_pg = self.get_dN_e_pg(matriceType)

                nPg = self.get_gauss(matriceType).nPg
                nPe = self.nPe
                dim = self.__get_dim()
                listnPe = np.arange(nPe)
                
                colonnes0 = np.arange(0, nPe*dim, dim)
                colonnes1 = np.arange(1, nPe*dim, dim)

                if self.dim == 2:
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

                import Materiau
                B_e_pg = Materiau.LoiDeComportement.AppliqueCoefSurBrigi(dim, B_e_pg)

                self.__dict_B_dep_e_pg[matriceType] = B_e_pg
            
            return cast(np.ndarray, self.__dict_B_dep_e_pg[matriceType]).copy()

        def get_leftDepPart(self, matriceType: str):
            """Renvoie la partie qui construit le therme de gauche de déplacement\n
            Ku_e = jacobien_e_pg * poid_pg * B_dep_e_pg' * c_e_pg * B_dep_e_pg\n
            
            Renvoie (epij) -> jacobien_e_pg * poid_pg * B_dep_e_pg'
            """

            assert matriceType in GroupElem.get_MatriceType()

            if matriceType not in self.__dict_leftDepPart.keys():
                
                jacobien_e_pg = self.get_jacobien_e_pg(matriceType)
                poid_pg = self.get_gauss(matriceType).poids
                B_dep_e_pg = self.get_B_dep_e_pg(matriceType)

                leftDepPart = np.einsum('ep,p,epij->epji', jacobien_e_pg, poid_pg, B_dep_e_pg, optimize='optimal')

                self.__dict_leftDepPart[matriceType] = leftDepPart

            return cast(np.ndarray, self.__dict_leftDepPart[matriceType])
                
             
        
        def get_phaseField_ReactionPart_e_pg(self, matriceType: str):
            """Renvoie la partie qui construit le therme de reaction\n
            ReactionPart_e_pg = jacobien_e_pg * poid_pg * r_e_pg * Nd_pg' * Nd_pg\n
            
            Renvoie -> jacobien_e_pg * poid_pg * Nd_pg' * Nd_pg
            """

            assert matriceType in GroupElem.get_MatriceType()

            if matriceType not in self.__dict_phaseField_ReactionPart_e_pg.keys():

                jacobien_e_pg = self.get_jacobien_e_pg(matriceType)
                poid_pg = self.get_gauss(matriceType).poids
                Nd_pg = self.get_N_pg(matriceType, 1)

                ReactionPart_e_pg = np.einsum('ep,p,pki,pkj->epij', jacobien_e_pg, poid_pg, Nd_pg, Nd_pg, optimize='optimal')

                self.__dict_phaseField_ReactionPart_e_pg[matriceType] = ReactionPart_e_pg
            
            return cast(np.ndarray, self.__dict_phaseField_ReactionPart_e_pg[matriceType]).copy()
        
        def get_phaseField_DiffusePart_e_pg(self, matriceType: str):
            """Renvoie la partie qui construit le therme de diffusion\n
            DiffusePart_e_pg = jacobien_e_pg * poid_pg * k * Bd_e_pg' * Bd_e_pg\n
            
            Renvoie -> jacobien_e_pg * poid_pg * Bd_e_pg' * Bd_e_pg
            """

            assert matriceType in GroupElem.get_MatriceType()

            if matriceType not in self.__dict_phaseField_DiffusePart_e_pg.keys():

                jacobien_e_pg = self.get_jacobien_e_pg(matriceType)
                poid_pg = self.get_gauss(matriceType).poids
                Bd_e_pg = self.get_dN_e_pg(matriceType)

                DiffusePart_e_pg = np.einsum('ep,p,epki,epkj->epij', jacobien_e_pg, poid_pg, Bd_e_pg, Bd_e_pg, optimize='optimal')

                self.__dict_phaseField_DiffusePart_e_pg[matriceType] = DiffusePart_e_pg
            
            return cast(np.ndarray, self.__dict_phaseField_DiffusePart_e_pg[matriceType]).copy()

        def get_phaseField_SourcePart_e_pg(self, matriceType: str):
            """Renvoie la partie qui construit le therme de source\n
            SourcePart_e_pg = jacobien_e_pg, poid_pg, f_e_pg, Nd_pg'\n
            
            Renvoie -> jacobien_e_pg, poid_pg, Nd_pg'
            """

            assert matriceType in GroupElem.get_MatriceType()

            if matriceType not in self.__dict_phaseField_SourcePart_e_pg.keys():

                jacobien_e_pg = self.get_jacobien_e_pg(matriceType)
                poid_pg = self.get_gauss(matriceType).poids
                Nd_pg = self.get_N_pg(matriceType, 1)

                SourcePart_e_pg = np.einsum('ep,p,pij->epji', jacobien_e_pg, poid_pg, Nd_pg, optimize='optimal') #le ji a son importance pour la transposé

                self.__dict_phaseField_SourcePart_e_pg[matriceType] = SourcePart_e_pg
            
            return cast(np.ndarray, self.__dict_phaseField_SourcePart_e_pg[matriceType]).copy()
        
        def __get_sysCoord_sysCoordLocal(self):
            """Matrice de changement de base pour chaque element"""

            coordo = self.coordoGlob

            if self.elemType in ["SEG2","SEG3"]:

                points1 = coordo[self.__connect[:,0]]
                points2 = coordo[self.__connect[:,1]]

            elif self.elemType in ["TRI3","TRI6"]:

                points1 = coordo[self.__connect[:,0]]
                points2 = coordo[self.__connect[:,1]]
                points3 = coordo[self.__connect[:,2]]

            elif self.elemType in ["QUAD4","QUAD8"]:

                points1 = coordo[self.__connect[:,0]]
                points2 = coordo[self.__connect[:,1]]
                points3 = coordo[self.__connect[:,3]]

            if self.dim in [0,3]:
                sysCoord_e = np.eye(3)
                sysCoord_e = sysCoord_e[np.newaxis, :].repeat(self.Ne, axis=0)
                sysCoordLocal_e = sysCoord_e
            
            elif self.dim in [1,2]:

                i = points2-points1
                # Normalise
                i = np.einsum('ei,e->ei',i, 1/np.linalg.norm(i, axis=1), optimize='optimal')

                if self.dim == 1:
                    theta = np.pi/2
                    rot = np.array([[np.cos(theta), -np.sin(theta), 0],
                                    [np.sin(theta), np.cos(theta), 0],
                                    [0, 0, 1]])
                    j = np.einsum('ij,ej->ei',rot, i, optimize='optimal')
                else:
                    j = points3-points1
                    j = np.einsum('ei,e->ei',j, 1/np.linalg.norm(j, axis=1), optimize='optimal')
                    
                k = np.cross(i, j, axis=1)

                sysCoord_e = np.zeros((self.Ne, 3, 3))
                sysCoord_e[:,0] = i
                sysCoord_e[:,1] = j
                sysCoord_e[:,2] = k

                sysCoordLocal_e = sysCoord_e[:,range(self.dim)]

            return sysCoord_e, sysCoordLocal_e

        def __get_sysCoord(self):
            return self.__get_sysCoord_sysCoordLocal()[0]
        sysCoord_e = cast(np.ndarray, property(__get_sysCoord))

        def __get_sysCoordLocal(self):
            return self.__get_sysCoord_sysCoordLocal()[1]
        sysCoordLocal_e = cast(np.ndarray, property(__get_sysCoordLocal))

        def get_F_e_pg(self, matriceType: str):
            """Renvoie la matrice jacobienne
            """
            if self.dim == 0: return
            if matriceType not in self.__dict_F_e_pg.keys():

                nodes_n = self.__coordoGlob[:]

                nodes_e = nodes_n[self.__connect]

                if self.dim in [1,2] and nodes_n[:,self.dim].max() != 0:
                    syscoord = self.sysCoordLocal_e
                    nodes_e = np.einsum('eij,ekj->eik', nodes_e, syscoord, optimize='optimal')

                nodes_e = nodes_e[:,:,range(self.dim)]

                dN_pg = self.get_dN_pg(matriceType)

                F_e_pg = np.array(np.einsum('pik,ekj->epij', dN_pg, nodes_e, optimize='optimal'))                        
                
                self.__dict_F_e_pg[matriceType] = F_e_pg

            return cast(np.ndarray, self.__dict_F_e_pg[matriceType]).copy()
        
        def get_jacobien_e_pg(self, matriceType:str):
            """Renvoie les jacobiens
            """
            if self.dim == 0: return
            if matriceType not in self.__dict_jacobien_e_pg.keys():

                F_e_pg = self.get_F_e_pg(matriceType)

                jacbobien_e_pg = np.array(np.linalg.det(F_e_pg))

                self.__dict_jacobien_e_pg[matriceType] = jacbobien_e_pg

            return cast(np.ndarray, self.__dict_jacobien_e_pg[matriceType]).copy()
        
        def get_invF_e_pg(self, matriceType: str):
            """Renvoie l'inverse de la matrice jacobienne
            """
            if self.dim == 0: return
            if matriceType not in self.__dict_invF_e_pg.keys():

                F_e_pg = self.get_F_e_pg(matriceType)

                if self.dim == 1:
                    invF_e_pg = 1/F_e_pg
                elif self.dim == 2:
                    # A = [alpha, beta          inv(A) = 1/det * [b, -beta
                    #      a    , b   ]                           -a  alpha]

                    Ne = F_e_pg.shape[0]
                    nPg = F_e_pg.shape[1]
                    invF_e_pg = np.zeros((Ne,nPg,2,2))

                    det = self.get_jacobien_e_pg(matriceType)

                    alpha = F_e_pg[:,:,0,0]
                    beta = F_e_pg[:,:,0,1]
                    a = F_e_pg[:,:,1,0]
                    b = F_e_pg[:,:,1,1]

                    invF_e_pg[:,:,0,0] = b
                    invF_e_pg[:,:,0,1] = -beta
                    invF_e_pg[:,:,1,0] = -a
                    invF_e_pg[:,:,1,1] = alpha

                    invF_e_pg = np.einsum('ep,epij->epij',1/det, invF_e_pg, optimize='optimal')                        
                elif self.dim == 3:
                    invF_e_pg = np.array(np.linalg.inv(F_e_pg))

                self.__dict_invF_e_pg[matriceType] = invF_e_pg

            return cast(np.ndarray, self.__dict_invF_e_pg[matriceType]).copy()

        def __get_N_pg(self, matriceType: str):
            """Fonctions de formes vectorielles (pg), dans la base (ksi, eta ...)\n
            [N1, N2, . . . ,Nn]
            """
            if self.dim == 0: return

            if self.elemType == "SEG2":

                N1t = lambda x: 0.5*(1-x)
                N2t = lambda x: 0.5*(1+x)

                Ntild = np.array([N1t, N2t])
            
            elif self.elemType == "SEG3":

                N1t = lambda x: -0.5*(1-x)*x
                N2t = lambda x: 0.5*(1+x)*x
                N3t = lambda x: (1+x)*(1-x)

                Ntild = np.array([N1t, N2t, N3t])

            elif self.elemType == "TRI3":

                N1t = lambda ksi,eta: 1-ksi-eta
                N2t = lambda ksi,eta: ksi
                N3t = lambda ksi,eta: eta
                
                Ntild = np.array([N1t, N2t, N3t])

            elif self.elemType == "TRI6":

                N1t = lambda ksi,eta: -(1-ksi-eta)*(1-2*(1-ksi-eta))
                N2t = lambda ksi,eta: -ksi*(1-2*ksi)
                N3t = lambda ksi,eta: -eta*(1-2*eta)
                N4t = lambda ksi,eta: 4*ksi*(1-ksi-eta)
                N5t = lambda ksi,eta: 4*ksi*eta
                N6t = lambda ksi,eta: 4*eta*(1-ksi-eta)
                
                Ntild = np.array([N1t, N2t, N3t, N4t, N5t, N6t])
            
            elif self.elemType == "QUAD4":

                N1t = lambda ksi,eta: (1-ksi)*(1-eta)/4
                N2t = lambda ksi,eta: (1+ksi)*(1-eta)/4
                N3t = lambda ksi,eta: (1+ksi)*(1+eta)/4
                N4t = lambda ksi,eta: (1-ksi)*(1+eta)/4
                
                Ntild = np.array([N1t, N2t, N3t, N4t])

            elif self.elemType == "QUAD8":

                N1t = lambda ksi,eta: (1-ksi)*(1-eta)*(-1-ksi-eta)/4
                N2t = lambda ksi,eta: (1+ksi)*(1-eta)*(-1+ksi-eta)/4
                N3t = lambda ksi,eta: (1+ksi)*(1+eta)*(-1+ksi+eta)/4
                N4t = lambda ksi,eta: (1-ksi)*(1+eta)*(-1-ksi+eta)/4
                N5t = lambda ksi,eta: (1-ksi**2)*(1-eta)/2
                N6t = lambda ksi,eta: (1+ksi)*(1-eta**2)/2
                N7t = lambda ksi,eta: (1-ksi**2)*(1+eta)/2
                N8t = lambda ksi,eta: (1-ksi)*(1-eta**2)/2
                
                Ntild =  np.array([N1t, N2t, N3t, N4t, N5t, N6t, N7t, N8t])                    

            elif self.elemType == "TETRA4":

                N1t = lambda x,y,z: 1-x-y-z
                N2t = lambda x,y,z: x
                N3t = lambda x,y,z: y
                N4t = lambda x,y,z: z

                Ntild = np.array([N1t, N2t, N3t, N4t])

            elif self.elemType == "HEXA8":

                N1t = lambda x,y,z: 1/8 * (1-x) * (1-y) * (1-z)
                N2t = lambda x,y,z: 1/8 * (1+x) * (1-y) * (1-z)
                N3t = lambda x,y,z: 1/8 * (1+x) * (1+y) * (1-z)
                N4t = lambda x,y,z: 1/8 * (1-x) * (1+y) * (1-z)
                N5t = lambda x,y,z: 1/8 * (1-x) * (1-y) * (1+z)
                N6t = lambda x,y,z: 1/8 * (1+x) * (1-y) * (1+z)
                N7t = lambda x,y,z: 1/8 * (1+x) * (1+y) * (1+z)
                N8t = lambda x,y,z: 1/8 * (1-x) * (1+y) * (1+z)

                Ntild = np.array([N1t, N2t, N3t, N4t, N5t, N6t, N7t, N8t])

            elif self.elemType == "PRISM6":

                N1t = lambda x,y,z: 1/2 * y * (1-x)
                N2t = lambda x,y,z: 1/2 * z * (1-x)
                N3t = lambda x,y,z: 1/2 * (1-y-z) * (1-x)
                N4t = lambda x,y,z: 1/2 * y * (1+x)
                N5t = lambda x,y,z: 1/2 * z * (1+x)
                N6t = lambda x,y,z: 1/2 * (1-y-z) * (1+x)
                
                # Ntild = np.array([N1t, N2t, N3t, N4t, N5t, N6t])
                Ntild = np.array([N3t, N1t, N2t, N6t, N4t, N5t])

                # dN1t = [lambda x,y,z: -1/2 * y,         lambda x,y,z: 1/2 * (1-x),      lambda x,y,z: 0]
                # dN2t = [lambda x,y,z: -1/2 * z,         lambda x,y,z: 0,                lambda x,y,z: 1/2 * (1-x)]
                # dN3t = [lambda x,y,z: -1/2 * (1-y-z),   lambda x,y,z: -1/2 * (1-x),     lambda x,y,z: -1/2 * (1-x)]
                # dN4t = [lambda x,y,z: 1/2 * y,          lambda x,y,z: 1/2 * (1+x),      lambda x,y,z: 0]
                # dN5t = [lambda x,y,z: 1/2 * z,          lambda x,y,z: 0,                lambda x,y,z: 1/2 * (1+x)]
                # dN6t = [lambda x,y,z: 1/2 * (1-y-z),    lambda x,y,z: -1/2 * (1+x),     lambda x,y,z: -1/2 * (1+x)]

                # dNtild = np.array([dN1t, dN2t, dN3t, dN4t, dN5t, dN6t])

            
            else:
                raise "Element inconnue"

            
            # Evalue aux points de gauss

            gauss = self.get_gauss(matriceType)            
            coord = gauss.coord
            nPg = gauss.nPg

            N_pg = np.zeros((nPg, 1, len(Ntild)))

            for pg in range(nPg):
                for n, Nt in enumerate(Ntild):                    
                    if coord.shape[1] == 1:
                        N_pg[pg, 0, n] = Nt(coord[pg,0])
                    elif coord.shape[1] == 2:
                        N_pg[pg, 0, n] = Nt(coord[pg,0], coord[pg,1])
                    elif coord.shape[1] == 3:
                        N_pg[pg, 0, n] = Nt(coord[pg,0], coord[pg,1], coord[pg,2])

            return N_pg
        
        def get_dN_pg(self, matriceType: str):
            """Dérivées des fonctions de formes dans l'element de référence (pg, dim, nPe), dans la base (ksi, eta ...) \n
            [Ni,ksi . . . Nn,ksi\n
            Ni,eta . . . Nn,eta]
            """
            if self.dim == 0: return

            if self.elemType == "SEG2":

                dN1t = [lambda x: -0.5]
                dN2t = [lambda x: 0.5]

                dNtild = np.array([dN1t, dN2t])
            
            elif self.elemType == "SEG3":

                dN1t = [lambda x: x-0.5]
                dN2t = [lambda x: x+0.5]
                dN3t = [lambda x: -2*x]

                dNtild = np.array([dN1t, dN2t, dN3t])

            elif self.elemType == "TRI3":

                dN1t = [lambda ksi,eta: -1, lambda ksi,eta: -1]
                dN2t = [lambda ksi,eta: 1,  lambda ksi,eta: 0]
                dN3t = [lambda ksi,eta: 0,  lambda ksi,eta: 1]

                dNtild = np.array([dN1t, dN2t, dN3t])

            elif self.elemType == "TRI6":

                dN1t = [lambda ksi,eta: 4*ksi+4*eta-3,  lambda ksi,eta: 4*ksi+4*eta-3]
                dN2t = [lambda ksi,eta: 4*ksi-1,        lambda ksi,eta: 0]
                dN3t = [lambda ksi,eta: 0,              lambda ksi,eta: 4*eta-1]
                dN4t = [lambda ksi,eta: 4-8*ksi-4*eta,  lambda ksi,eta: -4*ksi]
                dN5t = [lambda ksi,eta: 4*eta,          lambda ksi,eta: 4*ksi]
                dN6t = [lambda ksi,eta: -4*eta,         lambda ksi,eta: 4-4*ksi-8*eta]
                
                dNtild = np.array([dN1t, dN2t, dN3t, dN4t, dN5t, dN6t])
            
            elif self.elemType == "QUAD4":
                
                dN1t = [lambda ksi,eta: (eta-1)/4,  lambda ksi,eta: (ksi-1)/4]
                dN2t = [lambda ksi,eta: (1-eta)/4,  lambda ksi,eta: (-ksi-1)/4]
                dN3t = [lambda ksi,eta: (1+eta)/4,  lambda ksi,eta: (1+ksi)/4]
                dN4t = [lambda ksi,eta: (-eta-1)/4, lambda ksi,eta: (1-ksi)/4]
                
                dNtild = [dN1t, dN2t, dN3t, dN4t]

            elif self.elemType == "QUAD8":
                
                dN1t = [lambda ksi,eta: (1-eta)*(2*ksi+eta)/4,      lambda ksi,eta: (1-ksi)*(ksi+2*eta)/4]
                dN2t = [lambda ksi,eta: (1-eta)*(2*ksi-eta)/4,      lambda ksi,eta: -(1+ksi)*(ksi-2*eta)/4]
                dN3t = [lambda ksi,eta: (1+eta)*(2*ksi+eta)/4,      lambda ksi,eta: (1+ksi)*(ksi+2*eta)/4]
                dN4t = [lambda ksi,eta: -(1+eta)*(-2*ksi+eta)/4,    lambda ksi,eta: (1-ksi)*(-ksi+2*eta)/4]
                dN5t = [lambda ksi,eta: -ksi*(1-eta),               lambda ksi,eta: -(1-ksi**2)/2]
                dN6t = [lambda ksi,eta: (1-eta**2)/2,               lambda ksi,eta: -eta*(1+ksi)]
                dN7t = [lambda ksi,eta: -ksi*(1+eta),               lambda ksi,eta: (1-ksi**2)/2]
                dN8t = [lambda ksi,eta: -(1-eta**2)/2,              lambda ksi,eta: -eta*(1-ksi)]
                                
                dNtild = np.array([dN1t, dN2t, dN3t, dN4t, dN5t, dN6t, dN7t, dN8t])

            elif self.elemType == "TETRA4":
                
                dN1t = [lambda x,y,z: -1,   lambda x,y,z: -1,   lambda x,y,z: -1]
                dN2t = [lambda x,y,z: 1,    lambda x,y,z: 0,    lambda x,y,z: 0]
                dN3t = [lambda x,y,z: 0,    lambda x,y,z: 1,    lambda x,y,z: 0]
                dN4t = [lambda x,y,z: 0,    lambda x,y,z: 0,    lambda x,y,z: 1]

                dNtild = np.array([dN1t, dN2t, dN3t, dN4t])

            elif self.elemType == "HEXA8":
                
                dN1t = [lambda x,y,z: -1/8 * (1-y) * (1-z),   lambda x,y,z: -1/8 * (1-x) * (1-z),   lambda x,y,z: -1/8 * (1-x) * (1-y)]
                dN2t = [lambda x,y,z: 1/8 * (1-y) * (1-z),    lambda x,y,z: -1/8 * (1+x) * (1-z),    lambda x,y,z: -1/8 * (1+x) * (1-y)]
                dN3t = [lambda x,y,z: 1/8 * (1+y) * (1-z),    lambda x,y,z: 1/8 * (1+x) * (1-z),    lambda x,y,z: -1/8 * (1+x) * (1+y)]
                dN4t = [lambda x,y,z: -1/8 * (1+y) * (1-z),    lambda x,y,z: 1/8 * (1-x) * (1-z),    lambda x,y,z: -1/8 * (1-x) * (1+y)]
                dN5t = [lambda x,y,z: -1/8 * (1-y) * (1+z),    lambda x,y,z: -1/8 * (1-x) * (1+z),    lambda x,y,z: 1/8 * (1-x) * (1-y)]
                dN6t = [lambda x,y,z: 1/8 * (1-y) * (1+z),    lambda x,y,z: -1/8 * (1+x) * (1+z),    lambda x,y,z: 1/8 * (1+x) * (1-y)]
                dN7t = [lambda x,y,z: 1/8 * (1+y) * (1+z),    lambda x,y,z: 1/8 * (1+x) * (1+z),    lambda x,y,z: 1/8 * (1+x) * (1+y)]
                dN8t = [lambda x,y,z: -1/8 * (1+y) * (1+z),    lambda x,y,z: 1/8 * (1-x) * (1+z),    lambda x,y,z: 1/8 * (1-x) * (1+y)]

                dNtild = np.array([dN1t, dN2t, dN3t, dN4t, dN5t, dN6t, dN7t, dN8t])
            
            elif self.elemType == "PRISM6":

                dN1t = [lambda x,y,z: -1/2 * y,         lambda x,y,z: 1/2 * (1-x),      lambda x,y,z: 0]
                dN2t = [lambda x,y,z: -1/2 * z,         lambda x,y,z: 0,                lambda x,y,z: 1/2 * (1-x)]
                dN3t = [lambda x,y,z: -1/2 * (1-y-z),   lambda x,y,z: -1/2 * (1-x),     lambda x,y,z: -1/2 * (1-x)]
                dN4t = [lambda x,y,z: 1/2 * y,          lambda x,y,z: 1/2 * (1+x),      lambda x,y,z: 0]
                dN5t = [lambda x,y,z: 1/2 * z,          lambda x,y,z: 0,                lambda x,y,z: 1/2 * (1+x)]
                dN6t = [lambda x,y,z: 1/2 * (1-y-z),    lambda x,y,z: -1/2 * (1+x),     lambda x,y,z: -1/2 * (1+x)]

                # dNtild = np.array([dN1t, dN2t, dN3t, dN4t, dN5t, dN6t])
                dNtild = np.array([dN3t, dN1t, dN2t, dN6t, dN4t, dN5t])
                

            else:
                raise "Element inconnue"
                
            
            # Evaluation aux points de gauss
            gauss = self.get_gauss(matriceType)
            coord = gauss.coord

            dim = self.dim
            nPg = gauss.nPg

            dN_pg = np.zeros((nPg, dim, len(dNtild)))

            for pg in range(nPg):
                for n, Nt in enumerate(dNtild):
                    for d in range(dim):
                        func = Nt[d]                        
                        if coord.shape[1] == 1:
                            dN_pg[pg, d, n] = func(coord[pg,0])
                        elif coord.shape[1] == 2:
                            dN_pg[pg, d, n] = func(coord[pg,0], coord[pg,1])
                        elif coord.shape[1] == 3:
                            dN_pg[pg, d, n] = func(coord[pg,0], coord[pg,1], coord[pg,2])

            return dN_pg        

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

            noeuds = np.where(conditionsTotal)[0]
            
            return self.__nodes[noeuds].copy()
        
        def Get_Nodes_Point(self, point: Point) -> np.ndarray:

            coordo = self.__coordo

            noeud = np.where((coordo[:,0] == point.x) & (coordo[:,1] == point.y) & (coordo[:,2] == point.z))[0]

            return self.__nodes[noeud].copy()

        def Get_Nodes_Line(self, line: Line) -> np.ndarray:
            
            vectUnitaire = line.vecteurUnitaire

            coordo = self.__coordo

            vect = coordo-line.coordo[0]

            prodScalaire = np.einsum('i,ni-> n', vectUnitaire, vect, optimize='optimal')
            prodVecteur = np.cross(vect, vectUnitaire)
            norm = np.linalg.norm(prodVecteur, axis=1)

            eps = np.finfo(float).eps

            noeuds = np.where((norm<eps) & (prodScalaire>=-eps) & (prodScalaire<=line.length+eps))[0]

            return self.__nodes[noeuds].copy()
        
        def Get_Nodes_Domain(self, domain: Domain) -> np.ndarray:
            """Renvoie la liste de noeuds qui sont dans le domaine"""

            coordo = self.__coordo

            eps = np.finfo(float).eps

            noeuds = np.where(  (coordo[:,0] >= domain.pt1.x-eps) & (coordo[:,0] <= domain.pt2.x+eps) &
                                (coordo[:,1] >= domain.pt1.y-eps) & (coordo[:,1] <= domain.pt2.y+eps) &
                                (coordo[:,2] >= domain.pt1.z-eps) & (coordo[:,2] <= domain.pt2.z+eps))[0]
            
            return self.__nodes[noeuds].copy()

        def Get_Nodes_Circle(self, circle: Circle) -> np.ndarray:
            """Renvoie la liste de noeuds qui sont dans le cercle"""

            coordo = self.__coordo

            eps = np.finfo(float).eps

            noeuds = np.where(np.sqrt((coordo[:,0]-circle.center.x)**2+(coordo[:,1]-circle.center.y)**2+(coordo[:,2]-circle.center.z)**2)<=circle.diam/2+eps)

            return self.__nodes[noeuds]
        
        def Localise_sol_e(self, sol: np.ndarray):
            """localise les valeurs de noeuds sur les elements"""
            tailleVecteur = self.Nn * self.dim

            if sol.shape[0] == tailleVecteur:
                sol_e = sol[self.assembly_e]
            else:
                sol_e = sol[self.__connect]
            
            return sol_e

        def get_connectTriangle(self):
            """Transforme la matrice de connectivité pour la passer dans le trisurf en 2D\n
            Par exemple pour un quadrangle on construit deux triangles
            pour un triangle à 6 noeuds on construit 4 triangles\n

            Renvoie un dictionnaire par type
            """
            assert self.dim == 2
            dict_connect_triangle = {}
            if self.elemType == "TRI3":
                dict_connect_triangle[self.elemType] = self.__connect[:,[0,1,2]]
            elif self.elemType == "TRI6":
                dict_connect_triangle[self.elemType] = np.array(self.__connect[:, [0,3,5,3,1,4,5,4,2,3,4,5]]).reshape(-1,3)
            elif self.elemType == "QUAD4":
                dict_connect_triangle[self.elemType] = np.array(self.__connect[:, [0,1,3,1,2,3]]).reshape(-1,3)
            elif self.elemType == "QUAD8":
                dict_connect_triangle[self.elemType] = np.array(self.__connect[:, [4,5,7,5,6,7,0,4,7,4,1,5,5,2,6,6,3,7]]).reshape(-1,3)
            else:
                raise "Element inconnue"

            return dict_connect_triangle

        def get_connect_Faces(self):
            """Récupère les identifiants des noeud constuisant les faces et renvoie les faces pour chaque types d'elements

            Returns
            -------
            list de list
                Renvoie une liste de face
            """
            assert self.dim in [2,3]

            dic_connect_faces = {}

            nPe = self.nPe            
            if self.elemType in ["SEG2","SEG3","POINT"]:
                dic_connect_faces[self.elemType] = self.__connect.copy()
            elif self.elemType == "TRI3":
                dic_connect_faces[self.elemType] = self.__connect[:, [0,1,2,0]]
            elif self.elemType == "TRI6":
                dic_connect_faces[self.elemType] = self.__connect[:, [0,3,1,4,2,5,0]]
            elif self.elemType == "QUAD4":
                dic_connect_faces[self.elemType] = self.__connect[:, [0,1,2,3,0]]
            elif self.elemType == "QUAD8":
                dic_connect_faces[self.elemType] = self.__connect[:, [0,4,1,5,2,6,3,7,0]]
            elif self.elemType == "TETRA4":
                # Ici par elexemple on va creer 3 faces, chaque face est composé des identifiants des noeuds
                dic_connect_faces[self.elemType] = np.array(self.__connect[:, [0,1,2,0,1,3,0,2,3,1,2,3]]).reshape(self.Ne*nPe,-1)
            elif self.elemType == "HEXA8":
                # Ici par elexemple on va creer 6 faces, chaque face est composé des identifiants des noeuds                
                dic_connect_faces[self.elemType] = np.array(self.__connect[:, [0,1,2,3,0,1,5,4,0,3,7,4,6,2,3,7,6,2,1,5,6,7,4,5]]).reshape(-1,nPe)
            elif self.elemType == "PRISM6":
                # Ici il faut faire attention parce que cette element est composé de 2 triangles et 3 quadrangles
                dic_connect_faces["TRI3"] = np.array(self.__connect[:, [0,1,2,3,4,5]]).reshape(-1,3)
                dic_connect_faces["QUAD4"] = np.array(self.__connect[:, [0,2,5,3,0,1,4,3,1,2,5,4]]).reshape(-1,4)
                
            else:
                raise "Element inconnue"

            return dic_connect_faces

        ################################################ STATIC ##################################################

        @staticmethod
        def get_MatriceType():
            liste = ["rigi", "masse"]
            return liste

        @staticmethod
        def get_Types2D():
            """type d'elements disponibles en 2D"""
            liste2D = ["TRI3", "TRI6", "QUAD4", "QUAD8"]
            return liste2D
        
        @staticmethod
        def get_Types3D():
            """type d'elements disponibles en 3D"""
            liste3D = ["TETRA4", "HEXA8", "PRISM6"]
            return liste3D

        @staticmethod
        def Get_ElemInFos(gmshId: int):
                """Renvoie le nom le nombre de noeuds par element et la dimension de l'élement en fonction du type

                Args:
                    type (int): type de l'identifiant sur gmsh

                Returns:
                    tuple: (type, nPe, dim)
                """
                if gmshId == 1:
                    type = "SEG2"; nPe = 2; dim = 1
                elif gmshId == 2:
                    type = "TRI3"; nPe = 3; dim = 2
                elif gmshId == 3:
                    type = "QUAD4"; nPe = 4; dim = 2 
                elif gmshId == 4:
                    type = "TETRA4"; nPe = 4; dim = 3
                elif gmshId == 5:
                    type = "HEXA8"; nPe = 8; dim = 3
                elif gmshId == 6:
                    type = "PRISM6"; nPe = 6; dim = 3
                elif gmshId == 7:
                    type = "PYRA5"; nPe = 5; dim = 3
                elif gmshId == 8:
                    type = "SEG3"; nPe = 3; dim = 1
                elif gmshId == 9:
                    type = "TRI6"; nPe = 6; dim = 2
                elif gmshId == 10:
                    type = "QUAD9"; nPe = 9; dim = 2
                elif gmshId == 11:
                    type = "TETRA10"; nPe = 10; dim = 3
                elif gmshId == 12:
                    type = "CUBE27"; nPe = 27; dim = 3
                elif gmshId == 13:
                    type = "PRISM18"; nPe = 18; dim = 3
                elif gmshId == 14:
                    type = "PYRA14"; nPe = 17; dim = 3
                elif gmshId == 15:
                    type = "POINT"; nPe = 1; dim = 0
                elif gmshId == 16:
                    type = "QUAD8"; nPe = 8; dim = 2
                elif gmshId == 18:
                    type = "PRISM15"; nPe = 15; dim = 3
                elif gmshId == 19:
                    type = "PYRA13"; nPe = 13; dim = 3
                else: 
                    raise "Type inconnue"
                    
                return type, nPe, dim
        

