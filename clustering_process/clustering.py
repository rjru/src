from corpus.pubmed import *
import topic_modeling.lda
import numpy
from toolkit.export import matrix_to_pex
from theme_discovery.citation_based_method import readTopicSummary
from toolkit.vis_vector import *
from skbio import DistanceMatrix
from skbio.tree import nj
from toolkit.utility import *
from visualization.layout import *
from toolkit.export import *
from dtw import dtw
from scipy.spatial.distance import euclidean
from clustering_process.distances import *
from fastdtw import fastdtw

# each document has a set of themes buy they are in disorder. This method sorted themes by date
def getIdAndDatesOfThemesOrdered(topicsSumary):
    datesThemes = []
    idThemeOrdened = []
    for k in sorted(topicsSumary, key=lambda k: topicsSumary[k][2]):
        idThemeOrdened.append(k)  # for example idThemeOrdened[0] = 13 and with the same id 0 in datesTheme[0] = 1990.18 it is the minimum value
        datesThemes.append(topicsSumary[k][2])
    return (idThemeOrdened, datesThemes)

def getIdAndDatesOfDocOrdered(ldaInstance, pubmed, idToPmid):
    docAndDate = {}
    for d in range(ldaInstance.D):
        aux = {}
        pmid = idToPmid[d]
        year = pubmed.docs[pmid]['year']
        aux[0] = d
        aux[1] = pmid
        aux[2] = year
        docAndDate[d] = aux

    idDocOrdened = []
    datesDoc = []
    for k in sorted(docAndDate, key=lambda k: docAndDate[k][2]):
        idDocOrdened.append(k)  # for example idThemeOrdened[0] = 13 and with the same id 0 in datesTheme[0] = 1990.18 it is the minimum value
        datesDoc.append(docAndDate[k][2])
    return (idDocOrdened, datesDoc)

# this method ordened each descriptor of themes of each document by date
def getThemesOfDocsOrdered(listIdPmid, idThemeOrdened):
    docsThemesOrdened = []
    for doc in listIdPmid:
        docOrd = []
        for idOrd in idThemeOrdened:
            docOrd.append(doc[idOrd])
        docsThemesOrdened.append(docOrd)
    return docsThemesOrdened

def getDocOfThemesOrdered(idDocOrdened, themesDescript):
    DocOfThemesOrdered = []
    for theme in themesDescript:
        aux = []
        for i in range(0, len(theme)):
            aux.append(theme[idDocOrdened[i]])
        DocOfThemesOrdered.append(aux)
    return DocOfThemesOrdered

def getMatrixDist(docsThemesOrdened, distance_method):
    lenMuesta = len(docsThemesOrdened)
    dis_matrix = numpy.zeros((lenMuesta, lenMuesta))

    for v1 in range(0, lenMuesta):
        for v2 in range(0, lenMuesta):
            if v1 == v2:
                dis_matrix[v1][v2] = 0
            if v1 < v2:
                dist_temp, path = distance_method(docsThemesOrdened[v1], docsThemesOrdened[v2], dist=euclidean)
                #dist_temp = distance_method(docsThemesOrdened[v1], docsThemesOrdened[v2])
                dis_matrix[v1][v2] = dist_temp
                dis_matrix[v2][v1] = dist_temp

    return dis_matrix

def njWithRoot(dis_matrix, muestraPmid):
    # no culcula la distancia, solo le da un formato mas adecuado a las distancias con los ids
    muestraPmidStr = [str(i) for i in muestraPmid]
    dm = DistanceMatrix(dis_matrix.tolist(), muestraPmidStr)
    treeOrig = nj(dm, result_constructor=str)
    # ponerle raiz
    t = Tree(treeOrig)
    R = t.get_midpoint_outgroup()
    t.set_outgroup(R)
    # imprime el arbol
    #print(t)
    # imprime el newick
    tree = t.write(format=3)
    tree = Tree(tree, format=1)
    #print(tree)
    #a = newick_to_pairwise_nodes(tree)
    #print(a)
    return tree

def getMatrixByTime(docsOfThemesOrdened, topicsSumary, datesThemes):
    lenMuesta = len(docsOfThemesOrdened)
    dis_matrix = numpy.zeros((lenMuesta, lenMuesta))
    min_date = min(datesThemes)
    max_date = max(datesThemes)

    k = 1000

    for v1 in range(0, lenMuesta):
        for v2 in range(0, lenMuesta):
            if v1 == v2:
                dis_matrix[v1][v2] = 0
            if v1 < v2:
                date1 = topicsSumary[v1][2]
                date2 = topicsSumary[v2][2]

                if (date1-min_date) > (date2-min_date):
                    dist_temp = 1 - math.exp(-((date1-min_date)*360/k))#(dates[i]-min_date).days
                    dis_matrix[v1][v2] = dist_temp
                    dis_matrix[v2][v1] = dist_temp
                else:
                    dist_temp = 1 - math.exp(-((date2-min_date)*360/k))#(dates[j]-min_date).days
                    dis_matrix[v1][v2] = dist_temp
                    dis_matrix[v2][v1] = dist_temp

    return dis_matrix

def getTopDocsOfThemesOrdened(docsOfThemesOrdened):
    docsOfThemesOrdenedTop = []
    for theme in docsOfThemesOrdened:
        themeTop = []
        for i in range(0, len(theme)):
            if theme[i] > 0.001:
                themeTop.append(theme[i])
        docsOfThemesOrdenedTop.append(themeTop)
    return docsOfThemesOrdenedTop

def getMeta(pubmed, pmidToId, idToPmid, docsDescript, topicsSumary, docsOfThemesOrdened, nameThemes):
    metaDoc = {"pubmed": pubmed, "pmidToId": pmidToId,
               "idToPmid": idToPmid, "distributionDoc": docsDescript
               }
    metaTheme = {"topicsSumary": topicsSumary, "distributionThemes": docsOfThemesOrdened,  #themesDescriptTopOrd, #themesDescript,
                 "nameThemes": nameThemes#, "idThemeOrdened": idThemeOrdened, "datesThemes": datesThemes,
                 }
    return metaDoc, metaTheme

def getNameThemes(themesDescript):
    nameThemes = []
    for theme in range(0, len(themesDescript)):
        nameThemes.append("theme_"+str(theme))
    return nameThemes

if __name__ == '__main__':
    pubmed = getPubMedCorpus()  # load raw data
    #print(pubmed.docs[21172003])
    (pmidToId, idToPmid) = getCitMetaGraphPmidIdMapping(pubmed)
    ldaFilePath = os.path.join(variables.TEST_RESULT, 'pubmed_citation_lda_40_5001_5001_0.001_0.001_timeCtrl_3_4.5.lda')
    ldaInstance = topic_modeling.lda.readLdaEstimateFile(ldaFilePath)  # load lda result
    ldaTopicSumaryFilePath = os.path.join(variables.TEST_RESULT, 'pubmed_citation_lda_40_5001_5001_0.001_0.001_timeCtrl_3_4.5.lda_summary')
    topicsSumary = readTopicSummary(ldaTopicSumaryFilePath)  # load lda sumary for order descriptor by time

    # we get characteristic description of each document, this was calculated by lda before
    # the detail is that descriptor is in disorder
    docsDescript = ldaInstance.thetaEstimate  # the descriptor of each document is conformed by a set of themes
    themesDescript = ldaInstance.phiEstimate  # the descriptor of each themes is conformed by a set of citation

    (idThemeOrdened, datesThemes) = getIdAndDatesOfThemesOrdered(topicsSumary)  # idThemeOrdened are ids that are ordened by time and dataThemes are dates ordened by time
    (idDocOrdened, datesDoc) = getIdAndDatesOfDocOrdered(ldaInstance, pubmed, idToPmid)
    docsOfThemesOrdened = getDocOfThemesOrdered(idDocOrdened, themesDescript)
    docsOfThemesOrdenedTop = getTopDocsOfThemesOrdened(docsOfThemesOrdened)

    print('calculate matrix distance')
    dis_matrix = getMatrixDist(docsOfThemesOrdenedTop, fastdtw)  # for themes fastdtw (themesDescriptTopOrd) dist_euclidean (docsOfThemesOrdened) hellinger(docsOfThemesOrdened)
    dis_matrix_time = getMatrixByTime(docsOfThemesOrdened, topicsSumary, datesThemes)
    #print("matrix content")
    #print(dis_matrix)
    #print("matrix time")
    #print(dis_matrix_time)

    dis_matrix = (numpy.matrix(dis_matrix) + 2*numpy.matrix(dis_matrix_time))/2
    print(dis_matrix)
    a = numpy.asarray(dis_matrix)
    numpy.savetxt("dis_matrix.csv", a, delimiter=",")
    #print('generate image of document')
    #generateImageDistribution(docsThemesOrdened, datesThemes, list(idToPmid.values()))  # muestraPmid generate image about themes' distribution of each document

    #print('generate image of themes')
    # None pues en el caso de los temas solo es necesario las coordenadas del eje y
    #generateImageDistribution(themesDescript, None, [i for i in range(0, len(themesDescript))])  # muestraPmid generate image about themes' distribution of each document

    #print('save result pex format')
    #res = matrix_to_pex('matrix_of_docs', dis_matrix, muestraPmid)
    nameThemes = getNameThemes(themesDescript)
    # método para aplicar nj y ademas calcula la raiz, mejor dicho lo convierte en un árbol con raiz
    t = njWithRoot(dis_matrix, nameThemes)  # for themes
    metaDoc, metaTheme = getMeta(pubmed, pmidToId, idToPmid, docsDescript, topicsSumary, docsOfThemesOrdened, nameThemes)

    rootedTree = EteTreeToBinaryTree(t)  # since now, we use only themes
    radialLayout(rootedTree)
    jsonTree = treeToJsonPubmed(rootedTree, metaDoc, metaTheme)
    jsonfile = open("/result/test111.json", 'w')
    #print(jsonTree)
    jsonfile.write(jsonTree)
    #print("hello word")