# -*- coding: utf-8 -*-
""" Module containing functions related to halo mass definitions, 
the relations between halo mass and radius, and the variation of these 
relations with cosmology_obj and redshift. 

The functions contained in this module borrow heavily from the Colossus 
package developed by Benedikt Diemer, http://bdiemer.bitbucket.org. 
"""
from __future__ import (
	division, print_function, absolute_import, unicode_literals)

import numpy as np 
from astropy import cosmology
from astropy import units as u

from ....custom_exceptions import *

__all__ = (['density_threshold', 'delta_vir', 
	'halo_mass_to_halo_radius', 'halo_radius_to_halo_mass'])

__author__ = ['Benedikt Diemer', 'Andrew Hearin']

def density_threshold(cosmology_obj, redshift, mdef):
	"""
	The threshold density for a given spherical-overdensity mass definition.
	
	Parameters
	--------------
	cosmology_obj : object 
		Instance of an `~astropy.cosmology` object. 

	redshift: array_like
		Can be a scalar or a numpy array.

	mdef: str
		String specifying the halo mass definition, e.g., 'vir' or '200m'. 
		
	Returns
	---------
	rho: array_like
		The threshold density in physical :math:`M_{\odot}h^2/Mpc^3`. 
		Has the same dimensions as the input ``redshift``. 

	See also
	----------
	delta_vir: The virial overdensity in units of the critical density.
	"""

	try:
		assert isinstance(cosmology_obj, cosmology.core.FLRW)
	except AssertionError:
		msg = ("\nYour input ``cosmology_obj`` must be an instance of "
			"`~astropy.cosmology.core.FLRW`\n")
		raise HalotoolsError(msg)

	mdef_msg = ("\nYour input mdef = ``%s`` is not recognized.\n\n"
		"The string formatting of the ``mdef`` input must be one of the following:\n"
		"\n1. A positive integer followed by the letter ``m``," 
		"for the case where you wish to specify the integer multiple of the mean matter density,\n"
		"\n2. A positive integer followed by the letter ``c``," 
		"for the case where you wish to specify the integer multiple of the critical density,\n"
		"\n3. The string ``vir``, for the virial overdensity defined by Bryan & Norman (1998)\n")

	try:
		delta_multiple = int(mdef[:-1])
		if delta_multiple <= 0:
			raise HalotoolsError("\nYour density threshold must be a positive integer\n")
	except:
		if mdef != 'vir':
			raise HalotoolsError(mdef_msg)

	final_char = mdef[-1]
	try:
		assert final_char in ('c', 'm')
	except AssertionError:
		if mdef != 'vir':
			raise HalotoolsError(mdef_msg)


	rho_crit = cosmology_obj.critical_density(redshift)
	rho_crit = rho_crit.to(u.Msun/u.Mpc**3).value/cosmology_obj.h**2

	if mdef[-1] == 'c':
		delta = int(mdef[:-1])
		rho_threshold = rho_crit * delta

	elif mdef[-1] == 'm':
		rho_crit0 = cosmology_obj.critical_density0
		rho_crit0 = rho_crit0.to(u.Msun/u.Mpc**3).value/cosmology_obj.h**2
		delta = int(mdef[:-1])
		rho_m = cosmology_obj.Om(redshift)*rho_crit0
		rho_threshold = delta * rho_m

	elif mdef == 'vir':
		delta = delta_vir(cosmology_obj, redshift)
		rho_threshold = rho_crit * delta

	else:
		raise HalotoolsError(mdef_msg)

	return rho_threshold

def delta_vir(cosmology_obj, redshift):
	"""
	The virial overdensity in units of the critical density, 
	using the fitting formula of Bryan & Norman 1998.
	
	Parameters
	--------------
	cosmology_obj : object 
		Instance of an `~astropy.cosmology` object. 

	redshift: array_like
		Can be a scalar or a numpy array.
		
	Returns
	----------
	delta: array_like
		The virial overdensity. Has the same dimensions as the input ``redshift``. 

	See also
	-----------
	density_threshold: The threshold density for a given mass definition.
	"""
	
	x = cosmology_obj.Om(redshift) - 1.0
	delta = 18 * np.pi**2 + 82.0 * x - 39.0 * x**2

	return delta

def halo_mass_to_halo_radius(mass, cosmology_obj, redshift, mdef):
	"""
	Spherical overdensity radius as a function of the input mass. 

	Note that this function is independent of the form of the density profile.

	Parameters
	------------
	mass: array_like
		Total halo mass in :math:`M_{\odot}/h`; can be a number or a numpy array.

	cosmology_obj : object 
		Instance of an `~astropy.cosmology` object. 

	redshift: array_like
		Can either be a scalar, or a numpy array of the same dimension as the input ``mass``. 

	mdef: str
		String specifying the halo mass definition, e.g., 'vir' or '200m'. 
		
	Returns
	--------
	radius: array_like
		Halo radius in physical Mpc/h; has the same dimensions as input ``mass``.

	See also
	---------------
	halo_radius_to_halo_mass: Spherical overdensity radius from mass.
	"""
	
	rho = density_threshold(cosmology_obj, redshift, mdef)
	radius = (mass * 3.0 / 4.0 / np.pi / rho)**(1.0 / 3.0)

	return radius

def halo_radius_to_halo_mass(radius, cosmology_obj, redshift, mdef):
	"""
	Spherical overdensity mass as a function of the input radius. 

	Note that this function is independent of the form of the density profile.

	Parameters
	------------
	radius: array_like
		Halo radius in physical Mpc/h; can be a scalar or a numpy array.

	cosmology_obj : object 
		Instance of an `~astropy.cosmology` object. 

	redshift: array_like
		Can either be a scalar, or a numpy array of the same dimension as the input ``radius``. 

	mdef: str
		String specifying the halo mass definition, e.g., 'vir' or '200m'. 
		
	Returns
	---------
	mass: array_like
		Total halo mass in :math:`M_{\odot}/h`; has the same dimensions as the input ``radius``. 

	"""
	
	rho = density_threshold(cosmology_obj, redshift, mdef)
	mass = 4.0 / 3.0 * np.pi * rho * radius**3
	return mass

