"""Module for timing operations."""

import time
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

class Tic:

    def __init__(self):
        self.__start = time.time()

    @staticmethod
    def Get_time_unity(time: float) -> tuple[float, str]:
        """Returns time with unity"""
        if time > 1:
            if time < 60:
                unite = "s"
                coef = 1
            elif time > 60 and time < 3600:
                unite = "m"
                coef = 1/60
            elif time > 3600 and time < 86400:
                unite = "h"
                coef = 1/3600
            else:
                unite = "j"
                coef = 1/86400
        elif time < 1 and time > 1e-3:
            coef = 1e3
            unite = "ms"
        elif time < 1e-3:
            coef = 1e6
            unite = "µs"
        else:
            unite = "s"
            coef = 1

        return time*coef, unite

    def Tac(self, category="", text="", verbosity=False) -> float:
        """Get time from previous tic or tac."""

        tf = np.abs(self.__start - time.time())

        tfCoef, unite = Tic.Get_time_unity(tf)

        textWithTime = f"{text} ({tfCoef:.3f} {unite})"
        
        value = [text, tf]

        if category in Tic.__History:
            old = list(Tic.__History[category])
            old.append(value)
            Tic.__History[category] = old
        else:
            Tic.__History[category] = [value]
        
        self.__start = time.time()

        if verbosity:
            print(textWithTime)

        return tf
    
    @staticmethod
    def Clear() -> None:
        """Delete history"""
        Tic.__History = {}
    
    __History = {}
    """history = { category: list( [text, time] ) }"""
       
    @staticmethod
    def Resume(verbosity=True) -> str:
        """Builds the TicTac summary"""

        if Tic.__History == {}: return

        resume = ""

        for categorie in Tic.__History:
            histoCategorie = np.array(np.array(Tic.__History[categorie])[:,1] , dtype=np.float64)
            tempsCatégorie = np.sum(histoCategorie)
            tempsCatégorie, unite = Tic.Get_time_unity(tempsCatégorie)
            resumeCatégorie = f"{categorie} : {tempsCatégorie:.3f} {unite}"
            if verbosity: print(resumeCatégorie)
            resume += '\n' + resumeCatégorie

        return resume            

    @staticmethod
    def __plotBar(ax: plt.Axes, categories: list, temps: list, reps: int, titre: str) -> None:        

        # Axis parameters
        ax.xaxis.set_tick_params(labelbottom=False, labeltop=True, length=0)
        ax.yaxis.set_visible(False)
        ax.set_axisbelow(True)

        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_lw(1.5)

        ax.grid(axis = "x", lw=1.2)

        tempsMax = np.max(temps)

        # I want to display the text on the right if the time represents < 0.5 timeTotal
        # Otherwise, we'll display it on the left

        for i, (texte, tmps, rep) in enumerate(zip(categories, temps, reps)):
            # height=0.55
            # ax.barh(i, t, height=height, align="center", label=c)            
            ax.barh(i, tmps, align="center", label=texte)
            
            # We add a space at the end of the text
            espace = " "

            temps, unite = Tic.Get_time_unity(tmps/rep)

            
            if rep > 1:
                repTemps = f" ({rep} x {np.round(temps,2)} {unite})"
            else:
                repTemps = f" ({np.round(temps,2)} {unite})"

            texte = espace + texte + repTemps + espace

            if tmps/tempsMax < 0.6:
                ax.text(tmps, i, texte, color='black',
                verticalalignment='center', horizontalalignment='left')
            else:
                ax.text(tmps, i, texte, color='white',
                verticalalignment='center', horizontalalignment='right')

        # plt.legend()
        ax.set_title(titre)

    @staticmethod 
    def Plot_History(folder="", details=False) -> None:
        """Display history.

        Parameters
        ----------
        folder : str, optional
            save folder, by default ""
        details : bool, optional
            History details, by default True
        """

        import Display

        if Tic.__History == {}: return

        historique = Tic.__History        
        totalTime = []
        categories = list(historique.keys())

        # recovers the time for each category
        tempsCategorie = [np.sum(np.array(np.array(historique[c])[:,1] , dtype=np.float64)) for c in categories]

        categories = np.array(categories)[np.argsort(tempsCategorie)][::-1]

        for i, c in enumerate(categories):

            # c subcategory times
            timeSubCategory = np.array(np.array(historique[c])[:,1] , dtype=np.float64)
            totalTime.append(np.sum(timeSubCategory)) #somme tout les temps de cette catégorie

            subCategories = np.array(np.array(historique[c])[:,0] , dtype=str)

            # We build a table to sum them over the sub-categories
            dfSubCategory = pd.DataFrame({'sub-categories' : subCategories, 'time': timeSubCategory, 'rep': 1})
            dfSubCategory = dfSubCategory.groupby(['sub-categories']).sum()
            dfSubCategory = dfSubCategory.sort_values(by='time')
            subCategories = dfSubCategory.index.tolist()

            # print(dfSousCategorie)

            if len(subCategories) > 1 and details and totalTime[-1]>0:
                fig, ax = plt.subplots()
                Tic.__plotBar(ax, subCategories, dfSubCategory['time'].tolist(), dfSubCategory['rep'].tolist(), c)
            
                if folder != "":                        
                    Display.Save_fig(folder, f"TicTac{i}_{c}")

        # On construit un tableau pour les sommé sur les sous catégories
        dfCategorie = pd.DataFrame({'categories' : categories, 'time': totalTime})
        dfCategorie = dfCategorie.groupby(['categories']).sum()
        dfCategorie = dfCategorie.sort_values(by='time')
        categories = dfCategorie.index.tolist()
        
        fig, ax = plt.subplots()
        Tic.__plotBar(ax, categories, dfCategorie['time'], [1]*dfCategorie.shape[0], "Summary")

        if folder != "":            
            Display.Save_fig(folder, "TicTac_Summary")