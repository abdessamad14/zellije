"""Kaleidoscopic tiling of paths."""

import contextlib
import math

from affine import Affine

from .euclid import Point
from .path import Path


class PathTiler:
    def __init__(self, drawing):
        self.drawing = drawing

        self.path_pts = []
        self.transform = Affine.identity()
        self.curpt = None
        self.saved_state = []

    # Path creation.

    @property
    def paths(self):
        return [Path(pts) for pts in self.path_pts]

    def move_to(self, x, y):
        x, y = self.transform * (x, y)
        self.path_pts.append([])
        self.path_pts[-1].append(Point(x, y))
        self.curpt = x, y

    def line_to(self, x, y):
        x, y = self.transform * (x, y)
        self.path_pts[-1].append(Point(x, y))
        self.curpt = x, y

    def rel_line_to(self, dx, dy):
        x, y = ~self.transform * self.curpt
        self.line_to(x + dx, y + dy)

    def close_path(self):
        self.path_pts[-1].append(self.path_pts[-1][0])
        self.curpt = None

    def in_device(self, x, y):
        """Return the transformed coordinates."""
        return self.transform * (x, y)

    def in_user(self, x, y):
        return ~self.transform * (x, y)

    # Transformation.

    def translate(self, dx, dy):
        self.transform *= Affine.translation(dx, dy)

    def rotate(self, degrees):
        self.transform *= Affine.rotation(degrees)

    def scale(self, x, y):
        self.transform *= Affine.scale(x, y)

    def reflect_x(self, x):
        self.translate(x, 0)
        self.scale(-1, 1)
        self.translate(-x, 0)

    def reflect_y(self, y):
        self.translate(0, y)
        self.scale(1, -1)
        self.translate(0, -y)

    def reflect_xy(self, x, y):
        self.reflect_x(x)
        self.reflect_y(y)

    def reflect_line(self, p1, p2):
        """Reflect across the line from p1 to p2."""
        # https://en.wikipedia.org/wiki/Transformation_matrix#Reflection
        (p1x, p1y), (p2x, p2y) = p1, p2
        dx = p2x - p1x
        dy = p2y - p1y
        denom = dx * dx + dy * dy

        a = (dx * dx - dy * dy) / denom
        b = (2 * dx * dy) / denom

        self.translate(p1x, p1y)
        self.transform *= Affine(a, b, 0, b, -a, 0)
        self.translate(-p1x, -p1y)

    # Save/Restore.

    def save(self):
        self.saved_state.append(self.transform)

    def restore(self):
        self.transform = self.saved_state.pop()

    @contextlib.contextmanager
    def saved(self):
        self.save()
        try:
            yield
        finally:
            self.restore()

    # Tiling of draw functions.
    # http://www.quadibloc.com/math/images/wall17.gif
    # https://www.math.toronto.edu/drorbn/Gallery/Symmetry/Tilings/Sanderson/index.html

    def tile_p1(self, draw_func, vcol, vrow, buffer=None):
        """Repeatedly call draw_func to tile the drawing."""
        # Should compute exactly the grid of parallelograms needed, but I don't
        # know how yet.
        if buffer is None:
            buffer = 3
        dwgw, dwgh = self.drawing.get_size()
        (vrx, vry), (vcx, vcy) = vrow, vcol
        tiles_across = int(dwgw // vcx)
        tiles_down = int(dwgh // vry)
        for row in range(-buffer, tiles_across + buffer):
            for col in range(-buffer, tiles_down + buffer):
                with self.saved():
                    self.translate(row * vrx + col * vcx, row * vry + col * vcy)
                    draw_func(self)

    def tile_pmm(self, draw_func, dx, dy):
        def four_mirror(pt):
            draw_func(pt)
            with pt.saved():
                pt.reflect_x(dx)
                draw_func(pt)
            with pt.saved():
                pt.reflect_xy(dx, dy)
                draw_func(pt)
            with pt.saved():
                pt.reflect_y(dy)
                draw_func(pt)

        self.tile_p1(four_mirror, (dx*2, 0), (0, dy*2), buffer=0)

    def tile_p6(self, draw_func, triw):
        def six_triangles(pt):
            pt.translate(0, triw)
            for _ in range(6):
                self.rotate(60)
                draw_func(pt)

        triw3 = triw * math.sqrt(3)
        self.tile_p1(six_triangles, (triw3, 0), (triw3 / 2, 1.5 * triw), buffer=2)

    def tile_p6m(self, draw_func, triw):
        def draw_mirrored(pt):
            draw_func(pt)
            with pt.saved():
                pt.reflect_x(0)
                draw_func(pt)

        self.tile_p6(draw_mirrored, triw)
