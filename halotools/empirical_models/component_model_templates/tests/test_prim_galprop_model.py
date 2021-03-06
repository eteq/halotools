#!/usr/bin/env python
import numpy as np
from astropy.table import Table
from copy import copy, deepcopy

from astropy.tests.helper import pytest
from astropy.table import Table 

from unittest import TestCase
import warnings 

from ..prim_galprop_model import PrimGalpropModel

from ....sim_manager import FakeSim
from ....custom_exceptions import HalotoolsError

__all__ = ['TestBinaryGalpropInterpolModel']


class TestPrimGalpropModel(TestCase):

    """ Class providing testing for the 
    `~halotools.empirical_models.PrimGalpropModel`. 
    """
    def setUp(self):

        class BaryonicMass(PrimGalpropModel):

            def __init__(self, **kwargs):
                galprop_name = 'baryonic_mass'
                PrimGalpropModel.__init__(self, galprop_name, **kwargs)

            def mean_baryonic_mass(self, **kwargs):
                try:
                    table = kwargs['table']
                    halo_mass = table[self.prim_haloprop_key]
                except KeyError:
                    halo_mass = kwargs['prim_haloprop']

                result = halo_mass/100.
                if 'table' in kwargs:
                    table['baryonic_mass'][:] = result
                else:
                    return result

        self.BaryonicMass = BaryonicMass

    def test_galprop_name1(self):

        model = self.BaryonicMass()
        assert hasattr(model, 'mc_baryonic_mass')

    def test_galprop_name2(self):

        model = self.BaryonicMass()
        assert 'mc_baryonic_mass' in model._mock_generation_calling_sequence

    def test_galprop_name3(self):

        model = self.BaryonicMass()
        assert 'baryonic_mass' in model._galprop_dtypes_to_allocate.names

    def test_mean_galprop_behavior1(self):

        model = self.BaryonicMass()

        halo_mass = np.logspace(10, 15, 100)

        baryonic_mass = model.mean_baryonic_mass(prim_haloprop = halo_mass)

    def test_mean_galprop_behavior2(self):

        model = self.BaryonicMass()

        halo_mass = np.logspace(10, 15, 100)

        baryonic_mass1 = model.mean_baryonic_mass(prim_haloprop = halo_mass)

        t = Table({model.prim_haloprop_key: halo_mass})
        t['baryonic_mass'] = 0.
        model.mean_baryonic_mass(table = t)

        assert np.all(t['baryonic_mass'] == baryonic_mass1)

    def test_mc_galprop_determinism1(self):

        model = self.BaryonicMass(redshift = 0)

        npts = int(1e2)
        halo_mass = np.zeros(npts) + 1e10

        mc_baryonic_mass1 = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=43)
        mc_baryonic_mass2 = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=43)

        assert np.allclose(mc_baryonic_mass1, mc_baryonic_mass2)

        mc_baryonic_mass3 = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=44)
        assert not np.allclose(mc_baryonic_mass1, mc_baryonic_mass3)

    def test_mc_galprop_determinism2(self):

        model = self.BaryonicMass(redshift = 0)

        npts = int(1e2)
        halo_mass = np.zeros(npts) + 1e10

        mc_baryonic_mass1 = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=43)
        mc_baryonic_mass2 = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=44)

        assert not np.allclose(mc_baryonic_mass1, mc_baryonic_mass2)

    def test_mc_galprop_consistency1(self):

        model = self.BaryonicMass(redshift = 0)

        npts = int(1e3)
        halo_mass = np.zeros(npts) + 1e10
        
        mean_baryonic_mass = model.mean_baryonic_mass(prim_haloprop = 1e10)

        mc_baryonic_mass = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=43)

        avg_baryonic_mass = mc_baryonic_mass.mean()
        assert np.allclose(avg_baryonic_mass, mean_baryonic_mass, rtol=0.2)

    def test_mc_galprop_consistency2(self):

        model = self.BaryonicMass(redshift = 0)

        npts = int(1e3)
        halo_mass = np.zeros(npts) + 1e10
        
        mc_baryonic_mass = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=43)

        measured_scatter = np.std(np.log10(mc_baryonic_mass))
        assert np.allclose(model.param_dict['scatter_model_param1'], 
            measured_scatter, 
            rtol=0.05)

    def test_param_dict_propagation(self):

        model = self.BaryonicMass(redshift = 0)

        npts = int(1e3)
        halo_mass = np.zeros(npts) + 1e10

        model.param_dict['scatter_model_param1'] = 0.01
        
        mc_baryonic_mass = model.mc_baryonic_mass(
            prim_haloprop = halo_mass, seed=43)

        measured_scatter = np.std(np.log10(mc_baryonic_mass))
        assert np.allclose(0.01, measured_scatter, rtol=0.05)


    def tearDown(self):
        pass










