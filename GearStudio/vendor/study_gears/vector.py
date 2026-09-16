from __future__ import annotations
import math


class Vector:
    def __init__(
        self,
        x: str | float | adsk.core.Vector3D | adsk.core.Point3D | Vector = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ):
        if isinstance(x, str):
            strs = x.removeprefix("(").removesuffix(")").split(",")
            self.x = float(strs[0])
            self.y = float(strs[1])
            self.z = float(strs[2])
            return
        if isinstance(x, float) or isinstance(x, int):
            self.x = x
            self.y = y
            self.z = z
            return
        self.x = x.x
        self.y = x.y
        self.z = x.z

    @classmethod
    def polar(cls, radius: float, t: float):
        return Vector(radius * math.cos(t), radius * math.sin(t))

    def __add__(self, other: Vector):
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector):
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float):
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float):
        return Vector(self.x / scalar, self.y / scalar, self.z / scalar)

    def __repr__(self):
        return f"Vector({self.x}, {self.y}, {self.z})"

    def __str__(self):
        return f"({self.x}, {self.y}, {self.z})"

    def __eq__(self, other: object):
        return (
            isinstance(other, Vector)
            and self.x == other.x
            and self.y == other.y
            and self.z == other.z
        )

    def __ne__(self, other: object):
        return not self == other

    def __neg__(self):
        return Vector(-self.x, -self.y, -self.z)

    def __abs__(self) -> float:
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    def __bool__(self):
        return self.x != 0 or self.y != 0 or self.z != 0

    def __getitem__(self, index: int):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        elif index == 2:
            return self.z
        else:
            raise IndexError("Invalid subscript")

    def __setitem__(self, index: int, value: float):
        if index == 0:
            self.x = value
        elif index == 1:
            self.y = value
        elif index == 2:
            self.z = value
        else:
            raise IndexError("Invalid subscript")

    def __iter__(self):
        return (i for i in (self.x, self.y, self.z))

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __len__(self):
        return 3

    def __copy__(self):
        return Vector(self.x, self.y, self.z)

    def __deepcopy__(self, memo):
        return Vector(self.x, self.y, self.z)

    def __format__(self, format_spec):
        components = (format(c, format_spec) for c in self)
        return f'({", ".join(components)})'

    def __round__(self, n: int = 0):
        return Vector(round(self.x, n), round(self.y, n), round(self.z, n))

    def norm(self):
        """
        Calculate the norm (length) of the vector.

        Returns:
            float: The length of the vector.
        """
        return abs(self)

    def angle(self):
        """
        Calculate the angle of the vector in radians.

        This method returns the angle between the positive x-axis and the vector
        (self.x, self.y) in the range [-pi, pi].

        Returns:
            float: The angle of the vector in radians.
        """
        return math.atan2(self.y, self.x)

    def slope(self):
        """
        Calculate the slope of the vector.

        The slope is defined as the ratio of the y-coordinate to the x-coordinate.

        Returns:
            float: The slope of the vector.

        Raises:
            ZeroDivisionError: If the x-coordinate is zero.
        """
        return self.y / self.x

    def distance(self, other: Vector):
        """
        Calculate the distance between this vector and another vector.

        Parameters:
        other (Vector): The other vector to calculate the distance to.

        Returns:
        float: The distance between the two vectors.
        """
        return abs(self - other)

    def dot(self, other: Vector):
        """
        Calculate the dot product of this vector and another vector.

        Args:
            other (Vector): The other vector to perform the dot product with.

        Returns:
            float: The dot product of the two vectors.
        """
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector):
        """
        Calculate the 3D cross product of this vector with another vector.

        The cross product of two 3D vectors results in a scalar value.

        Args:
            other (Vector): The other vector to perform the cross product with.

        Returns:
            Vector: The cross product.
        """
        return Vector(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def normalize(self, size=1.0):
        """
        Normalizes the vector to the given size.

        Parameters:
        size (float): The desired size of the normalized vector. Default is 1.0.

        Returns:
        Vector: A new vector with the same direction as the original but with the specified size.
        """
        return size * self / abs(self)

    def flip_x(self):
        """
        Flip the vector along the X-axis.

        Returns:
            Vector: A new vector with the X component negated.
        """
        return Vector(-self.x, self.y, self.z)

    def flip_y(self):
        """
        Flip the y-coordinate of the vector.

        Returns:
            Vector: A new vector with the y-coordinate negated.
        """
        return Vector(self.x, -self.y, self.z)

    def flip_z(self):
        """
        Flip the z-coordinate of the vector.

        Returns:
            Vector: A new vector with the z-coordinate negated.
        """
        return Vector(self.x, self.y, -self.z)

    def rotate(self, angle: float, origin: Vector | None = None) -> Vector:
        """
        Rotates the vector around z-axis by a given angle.

        Args:
            angle (float): The angle in radians by which to rotate the vector.
            origin (Vector | None): The origin point to rotate around. If None, rotates around the origin.

        Returns:
            Vector: A new vector that is the result of rotating
            the original vector by the given angle.
        """
        if origin is not None:
            return (self - origin).rotate(angle) + origin

        return Vector(
            self.x * math.cos(angle) - self.y * math.sin(angle),
            self.x * math.sin(angle) + self.y * math.cos(angle),
        )

    def add_rotated(self, angle: float, other: Vector):
        """
        Adds a z-axis rotated version of another vector to the current vector.

        Parameters:
        angle (float): The angle in degrees to rotate the other vector.
        other (Vector): The vector to be rotated and added.

        Returns:
        Vector: The result of adding the rotated vector to the current vector.
        """
        return self + other.rotate(angle)

    def rotate_axis(self, axis: Vector, angle: float):
        """rotate v around axis by angle (in radians)"""
        axis = axis.normalize()
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        dot = self.dot(axis)
        cross = self.cross(axis)
        return self * cos_a + cross * sin_a + axis * dot * (1 - cos_a)

    def to_polar(self):
        """
        Convert the vector to polar coordinates.

        Returns:
            tuple: A tuple containing the radius and angle of the vector.
        """
        return abs(self), self.angle()

    def distance_from_line(self, p1: Vector, p2: Vector):
        """
        Calculate the distance between a point and a line.

        This method calculates the shortest distance between the point and the line
        defined by two points.

        Args:
            p1 (Vector): The first point on the line.
            p2 (Vector): The second point on the line.

        Returns:
            float: The shortest distance between the point and the line.
        """
        return abs(
            (p2.y - p1.y) * self.x - (p2.x - p1.x) * self.y + p2.x * p1.y - p2.y * p1.x
        ) / abs(p2 - p1)

    def project_to_plane(self, origin: Vector, normal: Vector):
        """
        Project the vector onto a plane defined by an origin and a normal vector.

        Args:
            origin (Vector): A point on the plane.
            normal (Vector): The normal vector of the plane.

        Returns:
            Vector: The projection of the vector onto the plane.
        """
        d = self - origin
        return d - d.dot(normal) * normal + origin


def vec(x: float | adsk.core.Point3D | adsk.core.Vector3D = 0.0, y=0.0, z=0.0):
    """
    Create a 3D vector with the given x, y and z coordinates.

    Args:
        x (float): The x-coordinate of the vector.
        y (float): The y-coordinate of the vector.
        z (float): The z-coordinate of the vector.

    Returns:
        Vector: A 3D vector with the specified coordinates.
    """
    return Vector(x, y, z)


def polar(r: float, t: float):
    return Vector.polar(r, t)


def fit2d_by_line(points: list[Vector]):
    # fit points by a line without using numpy, returns (point, direction)
    n = len(points)
    if n < 2:
        return None
    x = y = xx = xy = 0.0
    for p in points:
        x += p.x
        y += p.y
        xx += p.x * p.x
        xy += p.x * p.y
    det = n * xx - x * x
    if det == 0:
        return None
    a = (n * xy - x * y) / det
    b = (y * xx - x * xy) / det
    return vec(0, b), vec(1, a)


def fit3d_by_line(points: list[Vector]):
    # fit points by a line without using numpy, returns (point, direction) by least square method
    n = len(points)
    if n < 2:
        return None
    x = y = z = xx = xy = xz = yy = yz = zz = 0.0
    for p in points:
        x += p.x
        y += p.y
        z += p.z
        xx += p.x * p.x
        xy += p.x * p.y
        xz += p.x * p.z
        yy += p.y * p.y
        yz += p.y * p.z
        zz += p.z * p.z
    det_x = yy * zz - yz * yz
    det_y = xx * zz - xz * xz
    det_z = xx * yy - xy * xy
    det_max = max(det_x, det_y, det_z)
    if det_max == 0:
        return None
    if det_max == det_x:
        a = (xz * yz - xy * zz) / det_x
        b = (xy * yz - xz * yy) / det_x
        return vec(0, 0, z / n), vec(1, a, b).normalize()
    elif det_max == det_y:
        a = (yz * xz - xy * zz) / det_y
        b = (xy * xz - yz * xx) / det_y
        return vec(0, y / n, 0), vec(a, 1, b).normalize()
    else:
        a = (yz * xy - xz * yy) / det_z
        b = (xz * xy - yz * xx) / det_z
        return vec(x / n, 0, 0), vec(a, b, 1).normalize()


def fit3d_by_plane(points: list[Vector]):
    # fit points by a plane without using numpy
    # https://math.stackexchange.com/questions/99299/best-fitting-plane-given-a-set-of-points
    n = len(points)
    if n < 3:
        return None
    centroid = sum(points, Vector()) / n
    xx = xy = xz = yy = yz = zz = 0
    for p in points:
        q = p - centroid
        xx += q.x * q.x
        xy += q.x * q.y
        xz += q.x * q.z
        yy += q.y * q.y
        yz += q.y * q.z
        zz += q.z * q.z
    det_x = yy * zz - yz * yz
    det_y = xx * zz - xz * xz
    det_z = xx * yy - xy * xy
    det_max = max(det_x, det_y, det_z)
    if det_max == 0:
        return None
    if det_max == det_x:
        a = (xz * yz - xy * zz) / det_x
        b = (xy * yz - xz * yy) / det_x
        normal = vec(1, a, b).normalize()
    elif det_max == det_y:
        a = (yz * xz - xy * zz) / det_y
        b = (xy * xz - yz * xx) / det_y
        normal = vec(a, 1, b).normalize()
    else:
        a = (yz * xy - xz * yy) / det_z
        b = (xz * xy - yz * xx) / det_z
        normal = vec(a, b, 1).normalize()
    return normal, centroid


def radius_from_3points(p1: Vector, p2: Vector, p3: Vector) -> float:
    a = (p1 - p2).norm()
    b = (p2 - p3).norm()
    c = (p3 - p1).norm()
    s = (a + b + c) / 2
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    return (a * b * c) / (4 * area)
