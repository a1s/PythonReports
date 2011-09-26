"""1-dimension segment layout"""
"""History (most recent first):
21-jan-2011 [luch]  created
"""
__version__ = "$Revision: 1.2 $"[11:-2]
__date__ = "$Date: 2011/09/26 16:01:59 $"[7:-2]


from operator import itemgetter


class SegmentLayout(object):
    """1-dimension stretchable segment layout

    C{SegmentLayout} calculates actual segment position depending on
    actual width of segments after stretching.

    Layout is based on segment dependency DAG (Directed Acyclic Graph).
    All segments that a segment depends on should be wholly at its left.

    Each segment has a non-negative gap to the nearest segment of those
    it depends on.  The gap is taken into account when the segment's actual
    width is positive.  Zero width segments are considered meaningless.

    Example: 1 depend on A and B, 2 depends on 1, Z depends on 1,
        3 depends on 2 and Z.

    Initial layout::
            |gap|  |g|    |g|
      :aaaa     1111 222222 333
      :bbbbbb          zzz
                   |gap|

    - A can become longer than B, gaps are the same::
      :aaaaaaa   1111 222222 333
      :b                zzz

    - 2 collapses::
      :aaaa     1111       333
      :bbbbbb          zzz

    - 1 collapses::
      :aaaa   222222 333
      :bbbbbb   zzz

    - A and B collapse::
      :   1111 222222 333
      :          zzz

    At present there is no way to avoid leading gap when A and B collapse
    other than make zero gap.

    >>> SegmentLayout({})()
    {}

    >>> SegmentLayout({(0, 1):[]})()
    {(0, 1): 0}

    >>> sl = SegmentLayout({(0, 1):[], (0, 2):[]})
    >>> sorted(sl().items())
    [((0, 1), 0), ((0, 2), 0)]

    >>> map_indexes = lambda items, indexes: dict(
    ...    (items[i], [items[j] for j in indexes.get(i, [])])
    ...    for i in xrange(len(items)))

    >>> sl = SegmentLayout(map_indexes([(0, 1), (1, 1)], {1:[0]}))
    >>> sorted(sl().items())
    [((0, 1), 0), ((1, 1), 1)]
    >>> sorted(sl(lambda s: s[1] * 2).items())
    [((0, 1), 0), ((1, 1), 2)]

    >>> sl = SegmentLayout(map_indexes([(0, 1), (2, 1)], {1:[0]}))
    >>> sorted(sl().items())
    [((0, 1), 0), ((2, 1), 2)]
    >>> sorted(sl(lambda s: s[1] * 2).items())
    [((0, 1), 0), ((2, 1), 3)]

    >>> sl = SegmentLayout(map_indexes([(0, 1, 4), (1, 1, 1)], {1:[0]}))
    >>> sorted(sl(lambda s: s[2]).items())
    [((0, 1, 4), 0), ((1, 1, 1), 4)]

    >>> sl = SegmentLayout(map_indexes([(0, 4, 1), (5, 1, 1)], {1:[0]}))
    >>> sorted(sl(lambda s: s[2]).items())
    [((0, 4, 1), 0), ((5, 1, 1), 2)]

    >>> sl = SegmentLayout(map_indexes(
    ...     [(0, 2, 5), (1, 3, 1), (5, 1, 1)], {2:[0, 1]}))
    >>> sorted(sl(lambda s: s[2]).items())
    [((0, 2, 5), 0), ((1, 3, 1), 1), ((5, 1, 1), 6)]

    >>> sl = SegmentLayout(map_indexes(
    ...     [(0, 1, 5), (1, 3, 0), (5, 1, 1)], {2:[0, 1]}))
    >>> sorted(sl(lambda s: s[2]).items())
    [((0, 1, 5), 0), ((1, 3, 0), 1), ((5, 1, 1), 6)]

    @ivar segments: list of C{(segment, leading gap, leading segments)},
        where
        - C{segment} is tuple that contents depends on C{__call__}'s argument
            C{actual_width_func}, but 0-element must be segment's left point
            position.
        - C{leading segments} is list of segments that the segment's position
            depends on.
        - C{leading gap} is distance from the segment's left point to
            the right point of the nearest leading segment at left.

    """
    def __init__(self, segments_graph):
        """Initialize C{segments} from C{segments_graph}

        @param segments_graph: maps a segment to list of segments that
            lead the segment, it is the segment left point depends on
            actual width and position of these segments.  It is DAG.

            There must be entry for every segment.

        """
        _gap = dict(leading_gaps(segments_graph.iterkeys()))
        self.segments = [
            (_segment, segments_graph[_segment], _gap[_segment])
            for _segment in toposort(segments_graph)]

    def __call__(self, actual_width_func=(lambda segment: segment[1])):
        """@return: map segments to their actual position

        @param actual_width_func: a function that returns actual width
            of every segment by the segment itself.

        """
        _x_left = {}
        _x_right = {}
        for (_seg, _pre, _gap) in self.segments:
            _width = actual_width_func(_seg)
            if _pre:
                _x = max(_x_right[_sp] for _sp in _pre) \
                    + (_gap if _width > 0 else 0)
            else:
                _x = _seg[0]
            _x_left[_seg] = _x
            _x_right[_seg] = _x + _width

        return _x_left


def leading_gaps(segments, x0=0):
    """@return: segment to leading gap mapping

    Leading gap for a segment is distance to the nearest whole segment
    at its left.  For segments that have no whole segments at their left
    the leading gap is a distance to C{x0}.

    @param segments: sequence of C{(x, width)} pairs.
        C{width} should not be negative.
    @param x0: point 0 on the X axis.

    >>> leading_gaps([])
    []
    >>> leading_gaps([(0, 0)])
    [((0, 0), 0)]
    >>> leading_gaps([(0, 0)], -1)
    [((0, 0), 1)]
    >>> leading_gaps([(0, 1), (1, 1)])
    [((0, 1), 0), ((1, 1), 0)]
    >>> leading_gaps([(1, 0), (2, 0)])
    [((1, 0), 1), ((2, 0), 1)]
    >>> leading_gaps([(0, 5), (1, 3), (2, 1)])
    [((0, 5), 0), ((1, 3), 1), ((2, 1), 2)]
    >>> leading_gaps([(0, 2), (1, 0), (3, 1)])
    [((0, 2), 0), ((1, 0), 1), ((3, 1), 1)]

    """
    segments = list(segments)
    if segments:
        x0 = min(x0, min(map(itemgetter(0), segments))) - 1
        _bound = (x0, 1)
        segments.append(_bound)
        _rv = [(_this, _this[0] - (_pre[-1][0] + _pre[-1][1]))
            for (_this, _pre) in preceding_segments(segments)
            if _pre and (_this is not _bound)]
    else:
        _rv = []
    return _rv

def preceding_segments(segments):
    """For each segment list of segments wholly at its left

    @param segments: tuple with at least 2 items -- C{x} and C{width}.

    @return: list of C{(segments, preceding segment list)} in order of
        C{(segment left point, segment right point)} pairs.

    >>> preceding_segments([])
    []
    >>> preceding_segments([(0, 1)])
    []
    >>> preceding_segments([(0, 1), (0, 1)])
    []
    >>> preceding_segments([(0, 1), (0, 2)])
    []
    >>> preceding_segments([(0, 2), (0, 1)])
    []
    >>> preceding_segments([(0, 1), (1, 1)])
    [((1, 1), [(0, 1)])]
    >>> preceding_segments([(0, 1), (0, 2), (3, 1)])
    [((3, 1), [(0, 1), (0, 2)])]

    """
    _events = [(_seg[0], _seg, 0) for _seg in segments] \
        + [(_seg[0] + _seg[1], _seg, 1) for _seg in segments]
    _events.sort()
    _last_finished_x = None
    _finished_segmets = []
    _rv = []
    for (_x, _seg, _finished) in _events:
        if _finished:
            _last_finished_x = _x
            _finished_segmets.append(_seg)
        elif _last_finished_x is not None:
            _rv.append((_seg, list(_finished_segmets)))
    return _rv


def toposort(directed_graph):
    """@return: vertexes of directed acyclic graph in C{toposort} order

    Directions should go from a dependent vertext to a vertex it depends on.

    >>> toposort({})
    []
    >>> toposort({0:[]})
    [0]
    >>> toposort({0:[1], 1:[]})
    [1, 0]
    >>> toposort({0:[1, 2], 1:[3], 2:[3], 3:[4, 5, 6], 4:[6], 5:[6], 6:[]})
    [6, 4, 5, 3, 1, 2, 0]

    """
    _vertex_order = []
    _visited = set()

    def _walk(vertex):
        if vertex not in _visited:
            _visited.add(vertex)
            for child in directed_graph[vertex]:
                _walk(child)
            _vertex_order.append(vertex)

    for _vertex in directed_graph:
        _walk(_vertex)
    return _vertex_order

# vim: set et sts=4 sw=4 :
