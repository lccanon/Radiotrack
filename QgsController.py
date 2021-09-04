# -*- coding: utf-8 -*

from random import randrange

from qgis.utils import iface
from qgis.core import QgsProject, QgsMessageLog
from qgis.core import QgsVectorLayer, QgsFeature, QgsField, edit
from qgis.core import QgsGeometry, QgsPoint, QgsPointXY, QgsWkbTypes
from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsMarkerSymbol
from .algorithmNewPoint import dst
from qgis.PyQt.QtCore import QVariant

from .csv_utils import labels

class QgsController:

    LINE_LAYER_BASE_NAME = "lines"
    POINT_LAYER_BASE_NAME = "points"
    INTER_LAYER_BASE_NAME = "intersections"

    def __init__(self):
        # Store references to the layers
        self.layerLine = None
        self.layerPoint = None
        self.layerInter = None
        # Init geographical settings
        self.setEPSG4326()
        self.layerSuffix = ""
        # Autozoom and properties
        self.currExtent = None
        self.segmentLength = 1

    def setLayerSuffix(self, layerSuffix):
        """Indicate the suffix of all layers.

        Parameters
        ----------
        layerSuffix : str
            A suffix to add to all the layer created
        """
        self.layerSuffix = layerSuffix

    def createLayers(self, array):
        """Create a layer based on the given model rows.

        Parameters
        ----------
        array : list of TrackingModel items
        layerSuffix : str
            A potential suffix to add to all the layer created
        """

        # Draw the available points on their layers
        self.drawLines(array, self.LINE_LAYER_BASE_NAME + self.layerSuffix)
        self.drawPoints(array, self.POINT_LAYER_BASE_NAME + self.layerSuffix)
        self.setId(array)
        self.setFilter([row['id_observation'] for row in array], False)

    def clearLayers(self):
        self.clearLayer(self.layerLine)
        self.layerLine = None
        self.clearLayer(self.layerPoint)
        self.layerPoint = None
        self.clearLayer(self.layerInter)
        self.layerInter = None
        iface.mapCanvas().refresh()
        self.currExtent = None

    def clearLayer(self, layer):
        """Suppression d'un layer (clear)"""
        if layer is not None:
            try:
                QgsProject.instance().removeMapLayers([layer.id()])
            except:
                QgsMessageLog.logMessage('Layer already removed',
                                         'Radiotrack', level = QGis.Info)

    def drawLines(self, rows, layerName):
        """Draw the lines on a layer
        """

        # Specify the geometry type
        self.layerLine = QgsVectorLayer('LineString?crs=epsg:4326', layerName, 'memory')
        self.layerLine.setCrs(self.CRS)
        # Avoid warning when closing project
        self.layerLine.setCustomProperty("skipMemoryLayersCheck", 1)
        with edit(self.layerLine):
            self.layerLine.addAttribute(QgsField("id", QVariant.String))
            self.layerLine.addAttribute(QgsField("filter", QVariant.Int))
            self.layerLine.addAttribute(QgsField("biangulation", QVariant.Int))
        self.layerLine.setSubsetString('NOT filter')
        provLine = self.layerLine.dataProvider()

        # Create and add line features
        features = []
        for row in rows:
            newGeometry = self.makeLineGeometry(row)
            newFeature = QgsFeature()
            newFeature.setGeometry(newGeometry)
            features.append(newFeature)
        provLine.addFeatures(features)

        # Add the layer to the Layers panel
        QgsProject.instance().addMapLayers([self.layerLine])

        #XXX return fids here
        fids = [feature.id() for feature in self.layerLine.getFeatures()]

    def drawPoints(self, rows, layerName):
        """Draw the points on a layer
        """

        # Specify the geometry type
        self.layerPoint = QgsVectorLayer('Point?crs=epsg:4326', layerName, 'memory')
        self.layerPoint.setCrs(self.CRS)
        # Avoid warning when closing project
        self.layerPoint.setCustomProperty("skipMemoryLayersCheck", 1)
        with edit(self.layerPoint):
            self.layerPoint.addAttribute(QgsField("id", QVariant.String))
            self.layerPoint.addAttribute(QgsField("filter", QVariant.Int))
            self.layerPoint.addAttribute(QgsField("biangulation", QVariant.Int))
        self.layerPoint.setSubsetString('NOT filter')
        provPoint = self.layerPoint.dataProvider()

        # Create and add point features
        features = []
        for row in rows:
            newGeometry = self.makePointGeometry(row)
            newFeature = QgsFeature()
            newFeature.setGeometry(newGeometry)
            features.append(newFeature)
        provPoint.addFeatures(features)

        # Custom idRenderer for colors
        self.idRenderer = QgsCategorizedSymbolRenderer()
        self.idRenderer.setClassAttribute("id")
        self.layerPoint.setRenderer(self.idRenderer)

        # Add the layer to the Layers panel
        QgsProject.instance().addMapLayers([self.layerPoint])

        #XXX return ids here (check this it the same as for line)
        ids = [feature.id() for feature in self.layerPoint.getFeatures()]

    def updateRowLinePoint(self, row):
        """Update the value of a single observation"""
        idRow = row['id_observation']

        newGeometry = self.makeLineGeometry(row)
        self.updateRowGeometry(self.layerLine, idRow, newGeometry)

        newGeometry = self.makePointGeometry(row)
        self.updateRowGeometry(self.layerPoint, idRow, newGeometry)

        """The current row geometries are updated when the row is edited.
        Thus, it is not an hidden row. Thus, if it has to be kept by the
        filter and the filtering will not be updated. In this case, we need
        to initialize the value to False."""
        self.setFilter([idRow], False)

    def updateRowGeometry(self, layer, idRow, geom):
        if layer is None:
            return
        layer.startEditing()
        layer.changeGeometry(idRow, geom)
        layer.commitChanges()
        layer.updateExtents()

    def makeLineGeometry(self, rowData):
        try:
            x = rowData[labels['X']]
            y = rowData[labels['Y']]
            azi = rowData[labels['AZIMUT']]
            xRes, yRes = dst(y, x, azi, self.segmentLength)
            point = QgsPoint(x, y)
            point2 = QgsPoint(yRes, xRes)
            return QgsGeometry.fromPolyline([point, point2])
        except:
            return QgsGeometry()

    def makePointGeometry(self, rowData):
        try:
            inX = rowData[labels['X']]
            inY = rowData[labels['Y']]
            return QgsGeometry.fromPointXY(QgsPointXY(inX, inY))
        except:
            return QgsGeometry()

    def setId(self, array):
        ids = set([cat.value() for cat in self.idRenderer.categories()])
        for row in array:
            if row['id'] not in ids:
                """Generate a random color such that the lightness is sufficient to
                read text when used in background. The sum of RGB is at
                least 256 (which is one third of the max lightness)."""
                rgb = randrange(256), randrange(256), randrange(256)
                lighter = max(0, 256 - sum(rgb)) // 3
                rgb = tuple(col + lighter for col in rgb)
                symbol = QgsMarkerSymbol.createSimple({'size' : "3.0",
                                                       'color' : "%d,%d,%d" % rgb})
                cat = QgsRendererCategory(row['id'], symbol, row['id'])
                self.idRenderer.addCategory(cat)
                ids.add(row['id'])

        fieldIdx = self.layerPoint.dataProvider().fieldNameIndex('id')
        attrs = {row['id_observation']: {fieldIdx: row['id']} for row in array}

        self.changeAttributeValues(self.layerLine, attrs)
        self.changeAttributeValues(self.layerPoint, attrs)

    def getIdColors(self):
        return {cat.value(): cat.symbol().color()
                for cat in self.idRenderer.categories()}

    def setFilter(self, idRows, isFiltered):
        if len(idRows) == 0 or self.layerPoint is None or self.layerLine is None:
            return

        # This assumes that the fieldIdx is the same in both layers
        fieldIdx = self.layerPoint.dataProvider().fieldNameIndex('filter')
        attrs = {featureId: {fieldIdx: isFiltered} for featureId in idRows}

        self.changeAttributeValues(self.layerLine, attrs)
        self.changeAttributeValues(self.layerPoint, attrs)

        # If zoom set has not changed (autozoom), adjust the zoom
        if self.autoZoom():
            self.updateZoom()

    def changeAttributeValues(self, layer, attrs):
        if layer is None:
            return
        layer.dataProvider().changeAttributeValues(attrs)
        layer.triggerRepaint()
        layer.updateExtents()

    def drawIntersection(self, biangs):
        #TODO add point idRenderer for color based on name
        #TODO add filtering depending on line
        self.clearLayer(self.layerInter)

        # Specify the geometry type
        layerName = self.LINE_LAYER_BASE_NAME + self.layerSuffix
        self.layerInter = QgsVectorLayer('Point?crs=epsg:4326',
                                         layerName, 'memory')
        self.layerInter.setCrs(self.CRS)
        # Avoid warning when closing project
        self.layerInter.setCustomProperty("skipMemoryLayersCheck", 1)

        provInter = self.layerInter.dataProvider()
        features = []
        for obs1, obs2 in biangs:
            geom1 = self.layerLine.getGeometry(obs1)
            geom2 = self.layerLine.getGeometry(obs2)
            newGeom = geom1.intersection(geom2)
            if newGeom.type() == QgsWkbTypes.PointGeometry:
                newFeat = QgsFeature()
                newFeat.setGeometry(newGeom)
                features.append(newFeat)
        provInter.addFeatures(features)

        QgsProject.instance().addMapLayers([self.layerInter])
        self.layerInter.triggerRepaint()

    def updateZoom(self):
        fullExtent = self.updateFullExtent()
        # Does not zoom to full extent because it does not integrate well
        # with a basemap
        iface.mapCanvas().zoomToFeatureExtent(fullExtent)
        self.currExtent = iface.mapCanvas().extent()

    def updateFullExtent(self):
        fullExtent = self.layerPoint.extent()
        fullExtent.combineExtentWith(self.layerLine.extent())
        # Assumes that the CRS is the same in both layers
        sourceCrs = self.layerPoint.crs()
        destCrs = QgsProject.instance().crs()
        xform = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
        geom = QgsGeometry.fromRect(fullExtent)
        return xform.transform(fullExtent)

    def autoZoom(self):
        if self.currExtent is None:
            return True
        currentExtent = iface.mapCanvas().extent()
        return currentExtent.contains(self.currExtent) and \
           self.currExtent.contains(currentExtent)

    def setSegmentLength(self, length):
        self.segmentLength = length

    def setEPSG4326(self):
        self.CRS = QgsCoordinateReferenceSystem('epsg:4326')
        self.updateCRS()

    def setProjectCRS(self):
        self.CRS = QgsProject.instance().crs()
        self.updateCRS()

    def updateCRS(self):
        if self.layerLine is None or self.layerPoint is None:
            return
        self.setCrs(self.layerLine, self.CRS)
        self.setCrs(self.layerPoint, self.CRS)
        if self.autoZoom():
            self.updateZoom()
        if self.layerInter is not None:
            self.setCrs(self.layerInter, self.CRS)

    def setCrs(self, layer, CRS):
        layer.setCrs(CRS)
        layer.triggerRepaint()
        layer.updateExtents()
