# -*- coding: utf-8 -*-
#    Copyright (C) 2013  Christian Ledermann
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
try:
    from itertools import izip_longest
except ImportError:
    from itertools import zip_longest as izip_longest
try:
    import simplejson as json
except ImportError:
    import json

from datetime import datetime, date
import dateutil.parser

try:
    long
except NameError:
    # Python 3
    long = int

try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str

# XXX Import the geometries from shapely if it is installed
# or otherwise from Pygeoif

from pygeoif import geometry

from pygeoif.geometry import as_shape as asShape




def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(*args, fillvalue=fillvalue)


class _CZMLBaseObject(object):

    def dumps(self):
        d = self.data()
        return json.dumps(d)

    def data(self):
        raise NotImplementedError

    def loads(self, data):
        packets = json.loads(data)
        self.load(packets)

    def load(self, data):
        raise NotImplementedError



class CZML(_CZMLBaseObject):
    """ CZML is a subset of JSON, meaning that a valid CZML document
    is also a valid JSON document. Specifically, a CZML document contains
    a single JSON array where each object-literal element in the array is
    a CZML packet."""

    packets = None

    def __init__(self, packets=None):
        if packets:
            for p in packets:
                self.append(p)
        else:
            self.packets = []


    def data(self):
        for p in self.packets:
            yield p.data()

    def dumps(self):
        d = list(self.data())
        return json.dumps(d)

    def load(self, data):
        self.packets = []
        for packet in data:
            p = CZMLPacket()
            p.load(packet)
            self.packets.append(p)

    def append(self, packet):
        if self.packets is None:
            self.packets = []
        if isinstance(packet, CZMLPacket):
            self.packets.append(packet)
        else:
            raise ValueError

class _DateTimeAware(_CZMLBaseObject):
    """ A baseclass for Date time aware objects """

    _epoch = None
    _nextTime = None
    _previousTime = None

    def __init__(self, epoch=None, nextTime=None, previousTime=None):
        self.epoch = epoch
        self.nextTime = nextTime
        self.previousTime = previousTime

    @property
    def epoch(self):
        """ Specifies the epoch to use for times specifies as seconds
        since an epoch. """
        if self._epoch:
            return self._epoch.isoformat()

    @epoch.setter
    def epoch(self, dt):
        if dt is None:
            self._epoch = None
        elif isinstance(dt, (date,datetime)):
            self._epoch = dt
        elif isinstance(dt, basestring):
            self._epoch = dateutil.parser.parse(dt)
        else:
            raise ValueError

    @property
    def nextTime(self):
        """The time of the next sample within this interval, specified as
        either an ISO 8601 date and time string or as seconds since epoch.
        This property is used to determine if there is a gap between samples
        specified in different packets."""
        if isinstance(self._nextTime, (date,datetime)):
            return self._nextTime.isoformat()
        elif isinstance(self._nextTime, (int, long, float)):
            return self._nextTime

    @nextTime.setter
    def nextTime(self, dt):
        if dt is None:
            self._nextTime = None
        elif isinstance(dt, (date,datetime)):
            self._nextTime = dt
        elif isinstance(dt, (int, long, float)):
            self._nextTime = dt
        elif isinstance(dt, basestring):
            try:
                self._nextTime = float(dt)
            except ValueError:
                self._nextTime = dateutil.parser.parse(dt)
        else:
            raise ValueError


    @property
    def previousTime(self):
        """The time of the previous sample within this interval, specified
        as either an ISO 8601 date and time string or as seconds since epoch.
        This property is used to determine if there is a gap between samples
        specified in different packets."""
        if isinstance(self._previousTime, (date,datetime)):
            return self._previousTime.isoformat()
        elif isinstance(self._previousTime, (int, long, float)):
            return self._previousTime

    @previousTime.setter
    def previousTime(self, dt):
        if dt is None:
            self._previousTime = None
        elif isinstance(dt, (date,datetime)):
            self._previousTime = dt
        elif isinstance(dt, (int, long, float)):
            self._previousTime = dt
        elif isinstance(dt, basestring):
            try:
                self._previousTime = float(dt)
            except ValueError:
                self._previousTime = dateutil.parser.parse(dt)
        else:
            raise ValueError


    def load(self, data):
        self.epoch = data.get('epoch', None)
        self.nextTime = data.get('nextTime', None)
        self.previousTime = data.get('previousTime', None)

    def data(self):
        d = {}
        if self.epoch:
            d['epoch'] = self.epoch
        if self.nextTime:
            d['nextTime'] = self.nextTime
        if self.previousTime:
            d['previousTime'] = self.previousTime
        return d



class _Coordinate(object):
    """ [Longitude, Latitude, Height] or [X, Y, Z] or
    [Time, Longitude, Latitude, Height] or [Time, X, Y, Z]
    """
    x = y = z = 0
    t = None

    def __init__(self, x, y=None, z=0, t=None):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        if t is None:
            self.t = None
        elif isinstance(t, (date,datetime)):
            self.t = t
        elif isinstance(t, (int, long, float)):
            self.t = float(t)
        elif isinstance(t, basestring):
            try:
                self.t = float(t)
            except ValueError:
                self.t = dateutil.parser.parse(t)
        else:
            raise ValueError


class _Coordinates(object):

    coords = None

    def __init__(self, coords):
        if isinstance(coords, (list, tuple)):
            try:
                float(coords[1])
                if len(coords) < 3:
                    self.coords = [_Coordinate(coords[0], coords[1])]
                elif len(coords) < 4:
                    self.coords = [_Coordinate(coords[0], coords[1], coords[2])]
                elif len(coords) == 4:
                    self.coords = [_Coordinate(coords[1], coords[2], coords[3], coords[0])]
                elif len(coords) >= 4:
                    self.coords = []
                    for coord in grouper(coords, 4):
                        self.coords.append(_Coordinate(coord[1], coord[2],
                                                coord[3], coord[0]))
            except TypeError:
                self.coords = []
                for coord in grouper(coords, 2):
                    geom = asShape(coord[1])
                    assert(isinstance(geom, geometry.Point))
                    self.coords.append(_Coordinate(*geom.coords[0], t=coord[0]))
        else:
            geom = asShape(coords)
            if isinstance(geom, geometry.Point):
                self.coords = [_Coordinate(*geom.coords[0])]

    def data(self):
        d = []
        if self.coords:
            for coord in self.coords:
                if isinstance(coord.t, (date,datetime)):
                     d.append(coord.t.isoformat())
                elif coord.t is None:
                    pass
                else:
                    d.append(coord.t)
                d.append(coord.x)
                d.append(coord.y)
                d.append(coord.z)
        return d






class Position(_DateTimeAware):
    """ The position of the object in the world. The position has no
    direct visual representation, but it is used to locate billboards,
    labels, and other primitives attached to the object. """


    # The reference frame in which cartesian positions are specified.
    # Possible values are "FIXED" and "INERTIAL". In addition, the value
    # of this property can be a hash (#) symbol followed by the ID of
    # another object in the same scope whose "position" and "orientation"
    # properties define the reference frame in which this position is defined.
    # This property is ignored when specifying position with any type other
    # than cartesian. If this property is not specified,
    # the default reference frame is "FIXED".
    referenceFrame = None

    _cartesian = None
    _cartographicRadians = None
    _cartographicDegrees = None


    def __init__(self, referenceFrame= None, cartesian=None,
            cartographicRadians=None, cartographicDegrees=None,
            epoch=None, nextTime=None, previousTime=None):
        super(Position, self).__init__(epoch, nextTime, previousTime)
        self.cartesian = cartesian
        self.cartographicRadians = cartographicRadians
        self.cartographicDegrees = cartographicDegrees
        self.referenceFrame = referenceFrame


    @property
    def cartesian(self):
        """ The position represented as a Cartesian [X, Y, Z] in the meters
        relative to the referenceFrame. If the array has three elements,
        the position is constant. If it has four or more elements, they
        are time-tagged samples arranged as
        [Time, X, Y, Z, Time, X, Y, Z, Time, X, Y, Z, ...],
        where Time is an ISO 8601 date and time string or seconds since epoch.
        """
        return self._cartesian

    @cartesian.setter
    def cartesian(self, geom):
        if geom is not None:
            self._cartesian = _Coordinates(geom)
        else:
            self._cartesian = None

    @property
    def cartographicDegrees(self):
        """The position represented as a WGS 84 Cartographic
        [Longitude, Latitude, Height] where longitude and latitude are in
        degrees and height is in meters. If the array has three elements,
        the position is constant. If it has four or more elements, they are
        time-tagged samples arranged as
        [Time, Longitude, Latitude, Height, Time, Longitude, Latitude, Height, ...],
        where Time is an ISO 8601 date and time string or seconds since epoch.
        """
        return self._cartographicDegrees

    @cartographicDegrees.setter
    def cartographicDegrees(self, geom):
        if geom is not None:
            self._cartographicDegrees = _Coordinates(geom)
        else:
            self._cartographicDegrees = None


    @property
    def cartographicRadians(self):
        """The position represented as a WGS 84 Cartographic
        [Longitude, Latitude, Height] where longitude and latitude are in
        radians and height is in meters. If the array has three elements,
        the position is constant. If it has four or more elements, they are
        time-tagged samples arranged as
        [Time, Longitude, Latitude, Height, Time, Longitude, Latitude, Height, ...],
        where Time is an ISO 8601 date and time string or seconds since epoch.
        """
        return self._cartographicRadians

    @cartographicRadians.setter
    def cartographicRadians(self, geom):
        if geom is not None:
            self._cartographicRadians = _Coordinates(geom)
        else:
            self._cartographicRadians = None

    def load(self, data):
        super(Position, self).load(data)
        self.cartographicDegrees = data.get('cartographicDegrees', None)
        self.cartographicRadians = data.get('cartographicRadians', None)
        self.cartesian = data.get('cartesian', None)


    def data(self):
        d = super(Position, self).data()
        if self.cartographicDegrees:
            d['cartographicDegrees'] = self.cartographicDegrees.data()
        if self.cartographicRadians:
            d['cartographicRadians'] = self.cartographicRadians.data()
        if self.cartesian:
            d['cartesian'] = self.cartesian.data()
        return d




class _Color(object):
    r = g = b = a = 0
    t = None

    def __init__(self, r, g, b, a=1, t=None, num=float):
        self.r = num(r)
        self.g = num(g)
        self.b = num(b)
        self.a = num(a)
        if t is None:
            self.t = None
        elif isinstance(t, (date,datetime)):
            self.t = t
        elif isinstance(t, (int, long, float)):
            self.t = float(t)
        elif isinstance(t, basestring):
            try:
                self.t = float(t)
            except ValueError:
                self.t = dateutil.parser.parse(t)
        else:
            raise ValueError



class _Colors(object):
    """ The color specified as an array of color components
    [Red, Green, Blue, Alpha].
    If the array has four elements, the color is constant.
    If it has five or more elements, they are time-tagged samples arranged as
    [Time, Red, Green, Blue, Alpha, Time, Red, Green, Blue, Alpha, ...],
    where Time is an ISO 8601 date and time string or seconds since epoch.
    """
    colors = None

    def __init__(self, colors, num=float):
        if isinstance(colors, (list, tuple)):
            if len(colors) == 3:
                self.colors = [_Color(colors[0], colors[1], colors[2], num=num)]
            elif len(colors) == 4:
                self.colors = [_Color(colors[0], colors[1], colors[2], colors[3], num=num)]
            elif len(colors) == 5:
                self.colors = [_Color(colors[1], colors[2], colors[3], colors[4], colors[0], num=num)]
            elif len(colors) >= 5:
                self.colors = []
                for color in grouper(colors, 5):
                    self.colors.append(_Color(color[1], color[2],
                                            color[3], color[4] ,color[0], num=num))
            else:
                raise ValueError
        elif colors is None:
            self.colors = None
        else:
            raise ValueError

    def data(self):
        d = []
        if self.colors:
            for color in self.colors:
                if isinstance(color.t, (date,datetime)):
                     d.append(color.t.isoformat())
                elif color.t is None:
                    pass
                else:
                    d.append(color.t)
                d.append(color.r)
                d.append(color.g)
                d.append(color.b)
                d.append(color.a)
        return d


class Color(_DateTimeAware):

    _rgba = None
    _rgbaf = None

    @property
    def rgba(self):
        """The color specified as an array of color components
        [Red, Green, Blue, Alpha] where each component is in the
        range 0-255. If the array has four elements, the color is constant.
        If it has five or more elements, they are time-tagged samples arranged as
        [Time, Red, Green, Blue, Alpha, Time, Red, Green, Blue, Alpha, ...],
        where Time is an ISO 8601 date and time string or seconds since epoch.
        """
        if self._rgba is not None:
            return self._rgba.data()

    @rgba.setter
    def rgba(self, colors):
        if colors is None:
            self._rgba = None
        else:
            self._rgba = _Colors(colors, num=int)

    @property
    def rgbaf(self):
        """The color specified as an array of color components
        [Red, Green, Blue, Alpha] where each component is in the
        range 0.0-1.0. If the array has four elements, the color is constant.
        If it has five or more elements, they are time-tagged samples
        arranged as
        [Time, Red, Green, Blue, Alpha, Time, Red, Green, Blue, Alpha, ...],
        where Time is an ISO 8601 date and time string or seconds since epoch.
        """
        if self._rgbaf is not None:
            return self._rgbaf.data()

    @rgbaf.setter
    def rgbaf(self, colors):
        if colors is None:
            self._rgbaf = None
        else:
            self._rgbaf = _Colors(colors, num=float)


    def data(self):
        d = super(Color, self).data()
        if self.rgba is not None:
            d['rgba'] = self.rgba
        if self.rgbaf is not None:
            d['rgbaf'] = self.rgbaf
        return d


    def load(self, data):
        super(Color, self).load(data)
        self.rgba = data.get('rgba', None)
        self.rgbaf = data.get('rgbaf', None)


class Scale(_DateTimeAware):
    """ The scale of the billboard. The scale is multiplied with the
    pixel size of the billboard's image. For example, if the scale is 2.0,
    the billboard will be rendered with twice the number of pixels,
    in each direction, of the image."""

    _number = None


    @property
    def number(self):
        """ The floating-point value. The value may be a single number,
        in which case the value is constant over the interval, or it may
        be an array. If it is an array and the array has one element,
        the value is constant over the interval. If it has two or more
        elements, they are time-tagged samples arranged as
        [Time, Value, Time, Value, ...], where Time is an ISO 8601 date
        and time string or seconds since epoch."""
        if isinstance(self._number, alist):
            val = []
            for d in grouper(self._number, 2):
                if isinstance(d[0], (int, long, float)):
                     val.append(d[0])
                else:
                     val.append(d[0].isoformat())
            return val
        else:
            return self._number

    @number.setter
    def number(self, data):
        self._number = []
        if isinstance(data, (list, tuple)):
            if len(data) > 1:
                for d in grouper(data, 2):
                    v = float(d[1])
                    t = d[0]
                    if isinstance(t, (date,datetime)):
                       t = t
                    elif isinstance(t, (int, long, float)):
                        t = float(t)
                    elif isinstance(t, basestring):
                        try:
                            t = float(t)
                        except ValueError:
                            t = dateutil.parser.parse(t)
                    else:
                        raise ValueError
                    self._number.append((t,v))
            else:
                self._number = float(data[0])
        else:
            self._number = float(data)

    def data(self):
        d = super(Scale, self).data()
        if self.number:
            d['number'] = self.number
        return d

class Billboard(_CZMLBaseObject):
    """A billboard, or viewport-aligned image. The billboard is positioned
    in the scene by the position property.
    A billboard is sometimes called a marker."""

    # The image displayed on the billboard, expressed as a URL.
    # For broadest client compatibility, the URL should be accessible
    # via Cross-Origin Resource Sharing (CORS).
    # The URL may also be a data URI.
    image = None

    # Whether or not the billboard is shown.
    show = None

    _color = None

    scale = None

    @property
    def color(self):
        """ The color of the billboard. This color value is multiplied
        with the values of the billboard's "image" to produce the
        final color."""
        if self._color is not None:
            return self._color.data()

    @color.setter
    def color(self, color):
        if isinstance(color, Color):
            self._color = color
        elif isinstance(color, dict):
            col = Color()
            col.load(color)
            self._color = col
        elif color is None:
            self._color = None
        else:
            raise TypeError

    #@property
    #def scale(self):
        #"""The scale of the billboard. The scale is multiplied with the
        #pixel size of the billboard's image. For example, if the scale is
        #2.0, the billboard will be rendered with twice the number of pixels,
        #in each direction, of the image."""
        #return self._scale

    #@scale.setter
    #def scale(self, data):
        #self._scale = Scale(data)

    def data(self):
        d = {}
        if self.show:
            d['show'] = True
        if self.show == False:
            d['show'] = False
        if self.image:
            d['image'] = self.image
        if self.scale: #XXX
            d['scale'] = self.scale
        if self.color is not None:
            d['color'] = self.color
        return d

    def load(self, data):
        self.show = data.get('show', None)
        self.image = data.get('image', None)
        self.scale = data.get('scale', None)
        self.color = data.get('color', None)

class _VPositions(object):
    """ The list of positions [X, Y, Z, X, Y, Z, ...] """

    coords = None

    def __init__(self, coords):
        if isinstance(coords, (list, tuple)):
            assert(len(coords) % 3 == 0)
            assert(len(coords) >= 6)
            for coord in coords:
                if isinstance(coord, (int, long, float)):
                    continue
                else:
                    raise ValueError
            self.coords = coords
        else:
            geom = asShape(coords)
            if isinstance(geom, geometry.Polygon):
                geom = geom.exterior
            if isinstance(geom, (geometry.LineString, geometry.LinearRing)):
                self.coords = []
                for coord in geom.coords:
                    if len(coord) == 2:
                        self.coords += [coord[0], coord[1], 0]
                    elif len(coord) == 3:
                        self.coords += coord
                    else:
                        raise ValueError

    def data(self):
        return self.coords


class VertexPositions(_CZMLBaseObject):
    """The world-space positions of vertices.
    The vertex positions have no direct visual representation, but they
    are used to define polygons, polylines, and other objects attached
    to the object."""

    #The reference frame in which cartesian positions are specified.
    #Possible values are "FIXED" and "INERTIAL".
    #In addition, the value of this property can be a hash (#) symbol
    #followed by the ID of another object in the same scope
    #whose "position" and "orientation" properties define the reference
    #frame in which this position is defined.
    #This property is ignored when specifying position with any type
    #other than cartesian. If this property is not specified,
    #the default reference frame is "FIXED".
    referenceFrame = None

    #The list of positions specified as references. Each reference is
    #to a property that defines a single position,
    #possible as it changes with time.
    references = None

    _cartesian = None
    _cartographicRadians = None
    _cartographicDegrees = None


    def __init__(self, referenceFrame = None,
            cartesian=None, cartographicRadians=None,
            cartographicDegrees=None, references=None):
        self.cartesian = cartesian
        self.cartographicRadians = cartographicRadians
        self.cartographicDegrees = cartographicDegrees
        self.referenceFrame = referenceFrame
        self.references = references


    @property
    def cartesian(self):
        """The list of positions represented as Cartesian
        [X, Y, Z, X, Y, Z, ...] in the meters
        relative to the referenceFrame.
        """
        return self._cartesian

    @cartesian.setter
    def cartesian(self, geom):
        if geom is not None:
            self._cartesian = _VPositions(geom)
        else:
            self._cartesian = None

    @property
    def cartographicDegrees(self):
        """The list of positions represented as WGS 84
        [Longitude, Latitude, Height, Longitude, Latitude, Height, ...]
        where longitude and latitude are in degrees and height is in meters.
        """
        return self._cartographicDegrees

    @cartographicDegrees.setter
    def cartographicDegrees(self, geom):
        if geom is not None:
            self._cartographicDegrees = _VPositions(geom)
        else:
            self._cartographicDegrees = None


    @property
    def cartographicRadians(self):
        """The list of positions represented as WGS 84
        [Longitude, Latitude, Height, Longitude, Latitude, Height, ...]
        where longitude and latitude are in radians and height is in meters.
        """
        return self._cartographicRadians

    @cartographicRadians.setter
    def cartographicRadians(self, geom):
        if geom is not None:
            self._cartographicRadians = _VPositions(geom)
        else:
            self._cartographicRadians = None

    def load(self, data):
        self.cartographicDegrees = data.get('cartographicDegrees', None)
        self.cartographicRadians = data.get('cartographicRadians', None)
        self.cartesian = data.get('cartesian', None)


    def data(self):
        d = {}
        if self.cartographicDegrees:
            d['cartographicDegrees'] = self.cartographicDegrees.data()
        if self.cartographicRadians:
            d['cartographicRadians'] = self.cartographicRadians.data()
        if self.cartesian:
            d['cartesian'] = self.cartesian.data()
        return d



class Orientation(_CZMLBaseObject):
    """The orientation of the object in the world.
    The orientation has no direct visual representation, but it is used
    to orient models, cones, and pyramids attached to the object."""

    pass

class Point(_CZMLBaseObject):
    """A point, or viewport-aligned circle.
    The point is positioned in the scene by the position property. """

    show = False
    _color = None
    _outlineColor = None

    # The width of the outline of the point.
    outlineWidth = None

    # The size of the point, in pixels.
    pixelSize = None

    @property
    def color(self):
        """ The color of the point."""
        if self._color is not None:
            return self._color.data()

    @color.setter
    def color(self, color):
        if isinstance(color, Color):
            self._color = color
        elif isinstance(color, dict):
            col = Color()
            col.load(color)
            self._color = col
        elif color is None:
            self._color = None
        else:
            raise TypeError

    @property
    def outlineColor(self):
        """ The color of the outline of the point."""
        if self._outlineColor is not None:
            return self._outlineColor.data()

    @outlineColor.setter
    def outlineColor(self, color):
        if isinstance(color, Color):
            self._outlineColor = color
        elif isinstance(color, dict):
            col = Color()
            col.load(color)
            self._outlineColor = col
        elif color is None:
            self._outlineColor = None
        else:
            raise TypeError




    def data(self):
        d = {}
        if self.show:
            d['show'] = True
        if self.show == False:
            d['show'] = False
        if self.color:
            d['color'] = self.color
        if self.pixelSize:
            d['pixelSize'] = self.pixelSize
        if self.outlineColor:
            d['outlineColor'] = self.outlineColor
        if self.outlineWidth:
            d['outlineWidth'] = self.outlineWidth

        return d

    def load(self, data):
        self.show = data.get('show', None)
        self.color = data.get('color', None)
        self.outlineColor = data.get('outlineColor', None)
        self.pixelSize = data.get('pixelSize', None)
        self.outlineWidth = data.get('outlineWidth', None)



class Label(_CZMLBaseObject):
    """ A string of text.
    The label is positioned in the scene by the position property."""

    text = None
    show = False

    def __init__(self, text=None, show=False):
        self.text = text
        self.show = show

    def data(self):
        d = {}
        if self.show:
            d['show'] = True
        if self.show == False:
            d['show'] = False
        if self.text:
            d['text'] = self.text
        return d

    def load(self, data):
        self.show = data.get('show', None)
        self.text = data.get('text', None)


class Polyline(_CZMLBaseObject):
    """ A polyline, which is a line in the scene composed of multiple segments.
    The vertices of the polyline are specified by the vertexPositions property.
    """

    #Whether or not the polyline is shown.
    show = False

    _color = None
    _outlineColor = None

    # The width of the outline of the polyline.
    outlineWidth = None

    # The width of the polyline.
    width = None

    @property
    def color(self):
        """The color of the polyline."""
        if self._color is not None:
            return self._color.data()

    @color.setter
    def color(self, color):
        if isinstance(color, Color):
            self._color = color
        elif isinstance(color, dict):
            col = Color()
            col.load(color)
            self._color = col
        elif color is None:
            self._color = None
        else:
            raise TypeError

    @property
    def outlineColor(self):
        """The color of the outline of the polyline."""
        if self._outlineColor is not None:
            return self._outlineColor.data()

    @outlineColor.setter
    def outlineColor(self, color):
        if isinstance(color, Color):
            self._outlineColor = color
        elif isinstance(color, dict):
            col = Color()
            col.load(color)
            self._outlineColor = col
        elif color is None:
            self._outlineColor = None
        else:
            raise TypeError




    def data(self):
        d = {}
        if self.show:
            d['show'] = True
        if self.show == False:
            d['show'] = False
        if self.color:
            d['color'] = self.color
        if self.width:
            d['width'] = self.width
        if self.outlineColor:
            d['outlineColor'] = self.outlineColor
        if self.outlineWidth:
            d['outlineWidth'] = self.outlineWidth

        return d

    def load(self, data):
        self.show = data.get('show', None)
        self.color = data.get('color', None)
        self.outlineColor = data.get('outlineColor', None)
        self.width = data.get('width', None)
        self.outlineWidth = data.get('outlineWidth', None)




class Path(_CZMLBaseObject):
    """A path, which is a polyline defined by the motion of an object over
    time. The possible vertices of the path are specified by the position
    property."""
    pass

class Polygon(_CZMLBaseObject):
    """A polygon, which is a closed figure on the surface of the Earth.
    The vertices of the polygon are specified by the vertexPositions property.
    """
    pass

class Cone(_CZMLBaseObject):
    """ A cone starts at a point or apex and extends in a circle of
    directions which all have the same angular separation from the Z-axis
    of the object to which the cone is attached. The cone may be capped
    at a radial limit, it may have an inner hole, and it may be only a
    part of a complete cone defined by clock angle limits. The apex
    point of the cone is defined by the position property and extends in
    the direction of the Z-axis as defined by the orientation property.
    """
    pass

class Pyramid(_CZMLBaseObject):
    """A pyramid starts at a point or apex and extends in a specified list
    of directions from the apex. Each pair of directions forms a face of
    the pyramid. The pyramid may be capped at a radial limit.
    """
    pass


class Camera(_CZMLBaseObject):
    """A camera."""
    pass



class CZMLPacket(_CZMLBaseObject):
    """  A CZML packet describes the graphical properties for a single
    object in the scene, such as a single aircraft.
    """

    # Each packet has an id property identifying the object it is describing.
    # IDs do not need to be GUIDs - URIs make good IDs - but they do need
    # to uniquely identify a single object within a CZML source and any
    # other CZML sources loaded into the same scope.
    # If an id is not specified, the client will automatically generate
    # a unique one. However, this prevents later packets from referring
    # to this object in order to, for example, add more data to it.
    # A single CZML stream or document can contain multiple packets with
    # the same id, describing different aspects of the same object.
    id = None

    # The availability property indicates when data for an object is available.
    # If data for an object is known to be available at the current animation
    # time, but the client does not yet have that data (presumably because
    # it will arrive in a later packet), the client will pause with a message
    # like "Buffering..." while it waits to receive the data. The property
    # can be a single string specifying a single interval, or an array
    # of strings representing intervals.
    availability = None

    _position = None

    _billboard = None

    # The world-space positions of vertices. The vertex positions have no
    # direct visual representation, but they are used to define polygons,
    # polylines, and other objects attached to the object.
    _vertexPositions = None

    # The orientation of the object in the world. The orientation has no
    # direct visual representation, but it is used to orient models,
    # cones, and pyramids attached to the object.
    orientation = None

    _point = None

    _label = None

    # A polyline, which is a line in the scene composed of multiple segments.
    # The vertices of the polyline are specified by the vertexPositions
    # property.
    _polyline = None

    # A path, which is a polyline defined by the motion of an object over
    # time. The possible vertices of the path are specified by the
    # position property.
    path = None

    # A polygon, which is a closed figure on the surface of the Earth.
    # The vertices of the polygon are specified by the vertexPositions
    # property.
    polygon = None

    # A cone. A cone starts at a point or apex and extends in a circle of
    # directions which all have the same angular separation from the Z-axis
    # of the object to which the cone is attached. The cone may be capped
    # at a radial limit, it may have an inner hole, and it may be only a
    # part of a complete cone defined by clock angle limits. The apex point
    # of the cone is defined by the position property and extends in the
    # direction of the Z-axis as defined by the orientation property.
    cone = None

    # A pyramid. A pyramid starts at a point or apex and extends in a
    # specified list of directions from the apex. Each pair of directions
    # forms a face of the pyramid. The pyramid may be capped at a radial limit.
    pyramid = None

    # A camera.
    camera = None




    def __init__(self, id=None, availability = None):
        self.id = id
        self.availability = availability


    @property
    def position(self):
        """The position of the object in the world. The position has no direct
        visual representation, but it is used to locate billboards, labels,
        and other primitives attached to the object.
        """
        if self._position is not None:
            return self._position.data()

    @position.setter
    def position(self, position):
        if isinstance(position, Position):
            self._position = position
        elif isinstance(position, dict):
            pos = Position()
            pos.load(position)
            self._position = pos
        elif position is None:
            self._position = None
        else:
            raise TypeError


    @property
    def label(self):
        """A string of text. The label is positioned in the scene by the
        position property."""
        if self._label is not None:
            return self._label.data()

    @label.setter
    def label(self, label):
        if isinstance(label, Label):
            self._label = label
        elif isinstance(label, dict):
            l = Label()
            l.load(label)
            self._label = l
        elif label is None:
            self._label = None
        else:
            raise TypeError



    @property
    def billboard(self):
        """A billboard, or viewport-aligned image. The billboard is positioned
        in the scene by the position property. A billboard is sometimes
        called a marker."""
        if self._billboard is not None:
            return self._billboard.data()

    @billboard.setter
    def billboard(self, billboard):
        if isinstance(billboard, Billboard):
            self._billboard = billboard
        elif isinstance(billboard, dict):
            bb = Billboard()
            bb.load(billboard)
            self._billboard = bb
        elif billboard is None:
            self._billboard = None
        else:
            raise TypeError

    @property
    def point(self):
        """A point, or viewport-aligned circle. The point is positioned in
        the scene by the position property."""
        if self._point is not None:
            return self._point.data()

    @point.setter
    def point(self, point):
        if isinstance(point, Point):
            self._point = point
        elif isinstance(point, dict):
            p = Point()
            p.load(point)
            self._point = p
        elif point is None:
            self._point = None
        else:
            raise TypeError

    @property
    def vertexPositions(self):
        """The world-space positions of vertices.
        The vertex positions have no direct visual representation,
        but they are used to define polygons, polylines,
        and other objects attached to the object."""
        if self._vertexPositions is not None:
            return self._vertexPositions.data()

    @vertexPositions.setter
    def vertexPositions(self, vpositions):
        if isinstance(vpositions, VertexPositions):
            self._vertexPositions = vpositions
        elif isinstance(vpositions, dict):
            p = VertexPositions()
            p.load(vpositions)
            self._vertexPositions = p
        elif vpositions is None:
            self._vertexPositions = None
        else:
            raise TypeError


    @property
    def polyline(self):
        """A polyline, which is a line in the scene composed of multiple segments.
        The vertices of the polyline are specified by the vertexPositions
        property."""
        if self._polyline is not None:
            return self._polyline.data()

    @polyline.setter
    def polyline(self, polyline):
        if isinstance(polyline, Polyline):
            self._polyline = polyline
        elif isinstance(polyline, dict):
            p = Polyline()
            p.load(polyline)
            self._polyline = p
        elif polyline is None:
            self._polyline = None
        else:
            raise TypeError



    def data(self):
        d = {}
        if self.id:
            d['id']= self.id
        #if self.availability is not None:
        #    d['availability'] = self.availability
        if self.billboard is not None:
            d['billboard'] = self.billboard
        if self.position is not None:
            d['position'] = self.position
        if self.label  is not None:
            d['label'] = self.label
        if self.point  is not None:
            d['point'] = self.point
        if self.vertexPositions  is not None:
            d['vertexPositions'] = self.vertexPositions
        if self.polyline  is not None:
            d['polyline'] = self.polyline
        return d


    def load(self, data):
        self.id = data.get('id', None)
        #self.availability = data.get('availability', None)
        self.billboard = data.get('billboard', None)
        self.position = data.get('position', None)
        self.label = data.get('label', None)
        self.point = data.get('point', None)
        self.vertexPositions = data.get('vertexPositions', None)
        self.polyline = data.get('polyline', None)

