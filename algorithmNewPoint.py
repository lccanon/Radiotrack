# -*- coding: utf-8 -*
from math import *
RADIAN_DE_LA_TERRE = 6371

"""
    Fonctionnalité inspiré du lien ci-dessous :
    http://www.movable-type.co.uk/scripts/latlong.html
"""

def dst(longitude, latitude, azimut, distance):
    """
        Calcul du nouveau point en fonction des paramètres d'un point (longitude, latitude, azimut, distance)
    """
    # Transformation des valeurs de degré en radian
    rLat = radians(latitude)
    rLong = radians(longitude)
    rAzimut = radians(azimut)
    quotient = distance/RADIAN_DE_LA_TERRE

    # Calcul de la latitude et de la longitude du second point
    rLat2 = asin(sin(rLat) * cos(quotient) + cos(rLat) * sin(quotient) * cos(rAzimut))
    param1 = cos(quotient) - sin(rLat) * sin(rLat2)
    param2 = sin(rAzimut) * sin(quotient) * cos(rLat)
    rLong2 = rLong + atan2(param2,param1)

    # Transformation des valeurs de radian en degré
    return degrees(rLat2), degrees(rLong2)
