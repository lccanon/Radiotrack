# -*- coding: utf-8 -*

from random import randrange

from qgis.utils import iface
from qgis.core import QgsProject, QgsMessageLog, Qgis
from qgis.core import QgsVectorLayer, QgsFeature, QgsField, edit
from qgis.core import QgsGeometry, QgsPoint, QgsPointXY, QgsWkbTypes
from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem
from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsMarkerSymbol
from .algorithmNewPoint import dst
from qgis.PyQt.QtCore import QVariant
from qgis.core import Qgis as QGis

from .csv_utils import labels

class QgsController:

    LINE_LAYER_BASE_NAME = 'lines'
    POINT_LAYER_BASE_NAME = 'points'
    INTER_LAYER_BASE_NAME = 'intersections'

    def __init__(self):
        # Store references to the layers
        self.layerLine = None
        self.layerPoint = None
        self.layerInter = None
        # Init geographical settings
        self.setEPSG4326()
        self.layerSuffix = ''
        # Autozoom and properties
        self.currExtent = None
        self.segmentLength = 1
        self.layerInterVisible = False

    def setLayerSuffix(self, layerSuffix):
        """Indicate the suffix of all layers.

        Parameters
        ----------
        layerSuffix : str
            A suffix to add to all the layer created
        """
        self.layerSuffix = layerSuffix

    def createLayers(self, array, triangs):
        """Create a layer based on the given model rows.

        Parameters
        ----------
        array : list of TrackingModel items
        triangs : dict containing all triangulation correspondences
        """

        # Create specific renderer for coloring depending on id
        self.idRendPoint = QgsCategorizedSymbolRenderer()
        self.idRendPoint.setClassAttribute('id')
        self.idRendInter = QgsCategorizedSymbolRenderer()
        self.idRendInter.setClassAttribute('id')

        # Draw the available points on their layers
        self.drawLines(array)
        self.drawPoints(array)
        self.drawIntersections(triangs)
        iface.layerTreeView().setLayerVisible(self.layerInter, self.layerInterVisible)

        # Setting the id
        self.setId(array)

        # If zoom set has not changed (autozoom), adjust the zoom
        if self.autoZoom():
            self.updateZoom()

    def clearLayers(self):
        self.clearLayer(self.layerInter)
        self.layerInter = None
        self.clearLayer(self.layerPoint)
        self.layerPoint = None
        self.clearLayer(self.layerLine)
        self.layerLine = None
        iface.mapCanvas().refresh()
        self.currExtent = None

    def clearLayer(self, layer):
        """Suppression d'un layer (clear)"""
        if layer is not None:
            try:
                QgsProject.instance().removeMapLayers([layer.id()])
            except:
                QgsMessageLog.logMessage('Layer already removed',
                                         'Radiotrack', level = Qgis.Info)

    def drawLines(self, rows):
        """Draw the lines on a layer
        """

        # Specify the geometry type
        layerName = self.LINE_LAYER_BASE_NAME + self.layerSuffix
        self.layerLine = QgsVectorLayer('LineString?crs=epsg:4326',
                                        layerName, 'memory')
        # Create and add lines
        geometries = [self.makeLineGeometry(row) for row in rows]

        self.initLayerFeatures(self.layerLine, geometries)

        #XXX return fids here
        fids = [feature.id() for feature in self.layerLine.getFeatures()]

    def drawPoints(self, rows):
        """Draw the points on a layer
        """

        # Specify the geometry type
        layerName = self.POINT_LAYER_BASE_NAME + self.layerSuffix
        self.layerPoint = QgsVectorLayer('Point?crs=epsg:4326',
                                         layerName, 'memory')
        # Create and add points
        geometries = [self.makePointGeometry(row) for row in rows]

        self.initLayerFeatures(self.layerPoint, geometries)

        # Custom renderer for colors
        self.layerPoint.setRenderer(self.idRendPoint)

        #XXX return ids here (check this it the same as for line)
        fids = [feature.id() for feature in self.layerPoint.getFeatures()]

    def drawIntersections(self, triangs):
        # Specify the geometry type
        layerName = self.INTER_LAYER_BASE_NAME + self.layerSuffix
        self.layerInter = QgsVectorLayer('Point?crs=epsg:4326',
                                         layerName, 'memory')

        # Create and add points
        geometries = self.computeIntersections(triangs).values()
        self.initLayerFeatures(self.layerInter, geometries)

        # Custom renderer for colors
        self.layerInter.setRenderer(self.idRendInter)

    def computeIntersections(self, triangs):
        """Compute all intersections between corresponding filtered lines."""
        geometries = {}
        fids = [feature.id() for feature in self.layerPoint.getFeatures()]
        for fid in fids:
            geom = QgsGeometry()
            if fid in triangs:
                geom1 = self.layerLine.getGeometry(fid)
                geom2 = self.layerLine.getGeometry(triangs[fid])
                newGeom = geom1.intersection(geom2)
                if newGeom.type() == QgsWkbTypes.PointGeometry:
                    geom = newGeom
            geometries[fid] = geom
        return geometries

    def initLayerFeatures(self, layer, geometries):
        features = [QgsFeature() for i in geometries]
        for geom, feat in zip(geometries, features):
            feat.setGeometry(geom)
        prov = layer.dataProvider()
        prov.addFeatures(features)
        # Specify the geometry type
        layer.setCrs(self.CRS)
        # Avoid warning when closing project
        layer.setCustomProperty('skipMemoryLayersCheck', 1)
        with edit(layer):
            layer.addAttribute(QgsField('id', QVariant.String))
            layer.addAttribute(QgsField('filter', QVariant.Int))
            layer.addAttribute(QgsField('triangulation', QVariant.Int))
        self.initFilter(layer)
        # Setting the filter must be called after initializing the
        # filter attributes
        layer.setSubsetString('NOT filter')

        # Add the layer to the Layers panel
        QgsProject.instance().addMapLayers([layer])

    def updateRowLinePoint(self, row):
        """Update the value of a single observation"""
        idRow = row['id_observation']

        newGeometry = self.makeLineGeometry(row)
        self.updateRowGeometry(self.layerLine, {idRow: newGeometry})

        newGeometry = self.makePointGeometry(row)
        self.updateRowGeometry(self.layerPoint, {idRow: newGeometry})

        """The current row geometries are updated when the row is edited.
        Thus, it is not an hidden row. Thus, if it has to be kept by the
        filter and the filtering will not be updated. In this case, we need
        to initialize the value to False."""
        self.setFilter([idRow], False)

    def updateIntersections(self, triangs):
        """This method is required to update manually the intersections
        anytime there is an update to the data (keeping track of each
        change would be too cumbersome).

        """
        # Create and add points
        geometries = self.computeIntersections(triangs)
        self.updateRowGeometry(self.layerInter, geometries)

    def updateRowGeometry(self, layer, geometries):
        if layer is None:
            return
        layer.startEditing()
        for idRow, geom in geometries.items():
            layer.changeGeometry(idRow, geom)
        layer.commitChanges()
        layer.updateExtents()

    def makeLineGeometry(self, rowData):
        try:
            x = rowData[labels['X']]
            y = rowData[labels['Y']]
            azi = rowData[labels['AZIMUT']]
            xRes, yRes = dst(x, y, azi, self.segmentLength)
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
        if len(array) == 0 or self.layerPoint is None:
            return

        self.updateRenderer(self.idRendPoint, [row['id'] for row in array], 3)
        self.updateRenderer(self.idRendInter, [row['id'] for row in array], 2)

        fieldIdx = self.layerPoint.dataProvider().fieldNameIndex('id')
        attrs = {row['id_observation']: {fieldIdx: row['id']} for row in array}

        self.changeAttributeValues(self.layerLine, attrs)
        self.changeAttributeValues(self.layerPoint, attrs)
        self.changeAttributeValues(self.layerInter, attrs)

    def updateRenderer(self, idRend, indexes, size):
        if len(indexes) == 0:
            return

        ids = set([cat.value() for cat in idRend.categories()])
        for id in indexes:
            if id not in ids:
                """Generate a random color such that the lightness is sufficient to
                read text when used in background. The sum of RGB is at
                least 256 (which is one third of the max lightness)."""
                rgb = randrange(256), randrange(256), randrange(256)
                lighter = max(0, 256 - sum(rgb)) // 3
                rgb = tuple(col + lighter for col in rgb)
                symbol = QgsMarkerSymbol.createSimple({'size' : str(size),
                                                       'color' : '%d,%d,%d' % rgb})
                cat = QgsRendererCategory(id, symbol, id)
                idRend.addCategory(cat)
                ids.add(id)

    def getIdColors(self):
        return {cat.value(): cat.symbol().color()
                for cat in self.idRendPoint.categories()}

    def initFilter(self, layer):
        """Initialize the filtering attribute to show all features (must be
        called before setting the filtering rule to get the list of
        feature ids).
        """
        if layer is None:
            return

        fieldIdx = layer.dataProvider().fieldNameIndex('filter')
        fids = [feature.id() for feature in layer.getFeatures()]
        attrs = {featureId: {fieldIdx: False} for featureId in fids}

        self.changeAttributeValues(layer, attrs)

    def setFilter(self, idRows, isFiltered):
        if len(idRows) == 0 or self.layerPoint is None:
            return

        # This assumes that the fieldIdx is the same in both layers
        fieldIdx = self.layerPoint.dataProvider().fieldNameIndex('filter')
        attrs = {featureId: {fieldIdx: isFiltered} for featureId in idRows}

        self.changeAttributeValues(self.layerLine, attrs)
        self.changeAttributeValues(self.layerPoint, attrs)
        self.changeAttributeValues(self.layerInter, attrs)

        # If zoom set has not changed (autozoom), adjust the zoom
        if self.autoZoom():
            self.updateZoom()

    def changeAttributeValues(self, layer, attrs):
        """Change the values of an attribute that can possibly impact the
        graphical output (filtering, renderer)"""
        if layer is None:
            return
        layer.dataProvider().changeAttributeValues(attrs)
        layer.triggerRepaint()
        layer.updateExtents()

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

    def toggleIntersectionsVisible(self):
        self.layerInterVisible = not self.layerInterVisible
        iface.layerTreeView().setLayerVisible(self.layerInter, self.layerInterVisible)
