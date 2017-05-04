'''
Created on 24/04/2014

@author: MMPE
'''
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from io import open
from builtins import range
from builtins import int
from future import standard_library
standard_library.install_aliases()

import numpy as np

class StFile(object):
    """Read HAWC2 St (beam element structural data) file

    Methods are autogenerated for:

    - r : curved length distance from main_body node 1 [m]
    - m : mass per unit length [kg/m]
    - x_cg : xc2-coordinate from C1/2 to mass center [m]
    - y_cg : yc2-coordinate from C1/2 to mass center [m]
    - ri_x : radius of gyration related to elastic center. Corresponds to rotation about principal bending xe axis [m]
    - ri_y : radius of gyration related to elastic center. Corresponds to rotation about principal bending ye axis [m]
    - xs : xc2-coordinate from C1/2 to shear center [m]. The shear center is the point where external forces only contributes to pure bending and no torsion.
    - ys : yc2-coordinate from C1/2 to shear center [m]. The shear center is the point where external forces only contributes to pure bending and no torsion.
    - E : modulus of elasticity [N/m2]
    - G : shear modulus of elasticity [N/m2]
    - Ix : area moment of inertia with respect to principal bending xe axis [m4]. This is the principal bending axis most parallel to the xc2 axis
    - Iy : area moment of inertia with respect to principal bending ye axis [m4]
    - K : torsional stiffness constant with respect to ze axis at the shear center [m4/rad]. For a circular section only this is identical to the polar moment of inertia.
    - kx : shear factor for force in principal bending xe direction [-]
    - ky : shear factor for force in principal bending ye direction [-]
    - A : cross sectional area [m2]
    - pitch : structural pitch about z_c2 axis. This is the angle between the xc2 -axis defined with the c2_def command and the main principal bending axis xe.
    - xe : xc2-coordinate from C1/2 to center of elasticity [m]. The elastic center is the point where radial force (in the z-direction) does not contribute to bending around the x or y directions.
    - ye : yc2-coordinate from C1/2 to center of elasticity [m]. The elastic center is the point where radial force (in the

    The autogenerated methods have the following structure

    def xxx(radius=None, mset=1, set=1):
        Parameters:
        -----------
        radius : int, float, array_like or None, optional
            Radius/radii of interest\n
            If int, float or array_like: values are interpolated to requested radius/radii
            If None (default): Values of all radii specified in st file returned
        mset : int, optional
            Main set number
        set : int, optional
            Sub set number


    Examples
    --------
    >>> stfile = StFile(r"tests/test_files/DTU_10MW_RWT_Blade_st.dat")
    >>> print (stfile.m()) # Interpolated mass at radius 36
    [ 1189.51054664  1191.64291781  1202.76694262  ... 15.42438683]
    >>> print (st.E(radius=36, mset=1, set=1))  # Elasticity interpolated to radius 36m
    8722924514.652649
    >>> print (st.E(radius=36, mset=1, set=2))  # Same for stiff blade set
    8.722924514652648e+17
    """
    def __init__(self, filename):
        with open (filename) as fid:
            txt = fid.read()
#         Some files sat
        no_maindata_sets = int(txt.strip()[0]) 
        assert no_maindata_sets == txt.count("#")
        self.main_data_sets = {}
        for mset in txt.split("#")[1:]:
            mset_nr = int(mset.strip().split()[0])
            set_data_dict = {}

            for set_txt in mset.split("$")[1:]:
                set_lines = set_txt.split("\n")
                set_nr, no_rows = map(int, set_lines[0].split()[:2])
                assert set_nr not in set_data_dict
                set_data_dict[set_nr] = np.array([set_lines[i].split() for i in range(1, no_rows + 1)], dtype=np.float)
            self.main_data_sets[mset_nr] = set_data_dict

        for i, name in enumerate("r m x_cg y_cg ri_x ri_y x_sh y_sh E G I_x I_y I_p k_x k_y A pitch x_e y_e".split()):
            setattr(self, name, lambda radius=None, mset=1, set=1, column=i: self._value(radius, column, mset, set))

    def _value(self, radius, column, mset_nr=1, set_nr=1):
        st_data = self.main_data_sets[mset_nr][set_nr]
        if radius is None:
            radius = self.radius(None, mset_nr, set_nr)
        return np.interp(radius, st_data[:, 0], st_data[:, column])

    def radius_st(self, radius=None, mset=1, set=1):
        r = self.main_data_sets[mset][set][:, 0]
        if radius is None:
            return r
        return r[np.argmin(np.abs(r - radius))]

    def to_str(self, mset=1, set=1):
        d = self.main_data_sets[mset][set]
        return "\n".join([("%12.5e "*d.shape[1]) % tuple(row) for row in d])


if __name__ == "__main__":
    import os
    st = StFile(os.path.dirname(__file__) + r"/tests/test_files/DTU_10MW_RWT_Blade_st.dat")
    print (st.m())
    print (st.E(radius=36, mset=1, set=1))  # Elastic blade
    print (st.E(radius=36, mset=1, set=2))  # stiff blade
    #print (st.radius())
    xyz = np.array([st.x_e(), st.y_e(), st.r()]).T[:40]
    n = 2
    xyz = np.array([st.x_e(None, 1, n), st.y_e(None, 1, n), st.r(None, 1, n)]).T[:40]
    #print (xyz)
    print (np.sqrt(np.sum((xyz[1:] - xyz[:-1]) ** 2, 1)).sum())
    print (xyz[-1, 2])
    print (np.sqrt(np.sum((xyz[1:] - xyz[:-1]) ** 2, 1)).sum() - xyz[-1, 2])
    print (st.x_e(67.8883), st.y_e(67.8883))
    #print (np.sqrt(np.sum(np.diff(xyz, 0) ** 2, 1)))
    print (st.pitch(67.8883 - 0.01687))
    print (st.pitch(23.2446))



    #print (st.)
    #print (st.)
