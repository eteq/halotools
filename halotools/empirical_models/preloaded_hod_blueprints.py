# -*- coding: utf-8 -*-
"""

Module containing some commonly used composite HOD model blueprints.

"""

from . import model_defaults, mock_factories, smhm_components
from . import hod_components as hoc
from . import gal_prof_factory as gpf
from . import halo_prof_components as hpc
from . import gal_prof_components as gpc

from ..sim_manager import sim_defaults

__all__ = ['Zheng07_blueprint', 'Leauthaud11_blueprint', 'Hearin15_blueprint']


def Zheng07_blueprint(threshold = model_defaults.default_luminosity_threshold, **kwargs):
    """ Blueprint for the simplest pre-loaded HOD model. 
    There are two populations, 
    centrals and satellites, with occupation statistics, 
    positions and velocities based on Kravtsov et al. (2004). 

    Documentation of the test suite of this blueprint can be found at 
    `~halotools.empirical_models.test_empirical_models.test_Zheng07_blueprint`

    Parameters 
    ----------
    threshold : float, optional 
        Luminosity threshold of the galaxy sample being modeled. 

    Returns 
    -------
    model_blueprint : dict 
        Dictionary containing instructions for how to build the model. 
        When model_blueprint is passed to `~halotools.empirical_models.HodModelFactory`, 
        the factory returns the Zheng07 model object. 

    Examples 
    --------
    >>> from halotools.empirical_models import preloaded_hod_blueprints
    >>> blueprint = preloaded_hod_blueprints.Zheng07_blueprint()
    >>> blueprint  = preloaded_hod_blueprints.Zheng07_blueprint(threshold = -19)
    """     

    ### Build model for centrals
    cen_key = 'centrals'
    cen_model_dict = {}
    # Build the occupation model
    occu_cen_model = hoc.Zheng07Cens(threshold = threshold)
    cen_model_dict['occupation'] = occu_cen_model
    # Build the profile model
    
    cen_profile = gpf.IsotropicGalProf(
        gal_type=cen_key, halo_prof_model=hpc.TrivialProfile)

    cen_model_dict['profile'] = cen_profile

    ### Build model for satellites
    sat_key = 'satellites'
    sat_model_dict = {}
    # Build the occupation model
    occu_sat_model = hoc.Zheng07Sats(threshold = threshold)
    sat_model_dict['occupation'] = occu_sat_model
    # Build the profile model
    sat_profile = gpf.IsotropicGalProf(
        gal_type=sat_key, halo_prof_model=hpc.NFWProfile)
    sat_model_dict['profile'] = sat_profile

    model_blueprint = {
        occu_cen_model.gal_type : cen_model_dict,
        occu_sat_model.gal_type : sat_model_dict, 
        'mock_factory' : mock_factories.HodMockFactory
        }

    return model_blueprint


def Leauthaud11_blueprint(threshold = model_defaults.default_stellar_mass_threshold, **kwargs):
    """ Blueprint for a Leauthaud11-style HOD model. 

    Parameters 
    ----------
    threshold : float, optional keyword argument
        Stellar mass threshold of the mock galaxy sample. 
        Default value is specified in the `~halotools.empirical_models.model_defaults` module.

    Returns 
    -------
    model_blueprint : dict 
        Dictionary containing instructions for how to build the model. 
        When model_blueprint is passed to `~halotools.empirical_models.HodModelFactory`, 
        the factory returns the Leauthaud11 model object. 

    Examples 
    --------
    >>> from halotools.empirical_models import preloaded_hod_blueprints
    >>> blueprint = preloaded_hod_blueprints.Leauthaud11_blueprint()
    >>> blueprint  = preloaded_hod_blueprints.Leauthaud11_blueprint(threshold = 11.25)
    """     

    ### Build model for centrals
    cen_key = 'centrals'
    cen_model_dict = {}
    # Build the occupation model
    occu_cen_model = hoc.Leauthaud11Cens(threshold = threshold)
    cen_model_dict['occupation'] = occu_cen_model
    # Build the profile model
    
    cen_profile = gpf.IsotropicGalProf(
        gal_type=cen_key, halo_prof_model=hpc.TrivialProfile)

    cen_model_dict['profile'] = cen_profile

    ### Build model for satellites
    sat_key = 'satellites'
    sat_model_dict = {}
    # Build the occupation model
    occu_sat_model = hoc.Leauthaud11Sats(threshold = threshold)
    sat_model_dict['occupation'] = occu_sat_model
    # Build the profile model
    sat_profile = gpf.IsotropicGalProf(
        gal_type=sat_key, halo_prof_model=hpc.NFWProfile)
    sat_model_dict['profile'] = sat_profile

    model_blueprint = {
        occu_cen_model.gal_type : cen_model_dict,
        occu_sat_model.gal_type : sat_model_dict, 
        'mock_factory' : mock_factories.HodMockFactory
        }

    return model_blueprint


def Hearin15_blueprint(central_assembias = True, satellite_assembias = True, 
    **kwargs):
    """ 
    HOD-style model in which central and satellite occupations statistics are assembly-biased. 

    Parameters 
    ----------
    threshold : float, optional
        Stellar mass threshold of the mock galaxy sample. 
        Default value is specified in the `~halotools.empirical_models.model_defaults` module.

    central_assembias : bool, optional 
        Boolean determining whether the model implements assembly biased occupations for centrals. 
        Default is True. 

    satellite_assembias : bool, optional 
        Boolean determining whether the model implements assembly biased occupations for satellites. 
        Default is True. 

    sec_haloprop_key : string, optional keyword argument 
        String giving the column name of the secondary halo property modulating 
        the occupation statistics of the galaxies. 
        Default value is specified in the `~halotools.empirical_models.model_defaults` module.

    split : float
        percentile at which to implement heavside 2-population assembly bias

    central_assembias_strength : float or list, optional 
        Fraction or list of fractions between -1 and 1 defining 
        the assembly bias correlation strength. Default is 0.5. 

    central_assembias_strength_abcissa : list, optional 
        Values of the primary halo property at which the assembly bias strength is specified. 
        Default is to assume a constant strength of 0.5. 

    satellite_assembias_strength : float or list, optional 
        Fraction or list of fractions between -1 and 1 defining 
        the assembly bias correlation strength. Default is 0.5. 

    satellite_assembias_strength_abcissa : list, optional 
        Values of the primary halo property at which the assembly bias strength is specified. 
        Default is to assume a constant strength of 0.5. 

    redshift : float, optional keyword argument 
        Redshift of the stellar-to-halo-mass relation. Default is 0. 

    Returns 
    -------
    model_blueprint : dict 
        Dictionary containing instructions for how to build the model. 
        When model_blueprint is passed to `~halotools.empirical_models.HodModelFactory`, 
        the factory returns the Hearin15 model object. 

    """     

    ##############################
    ### Build the occupation model
    if central_assembias is True:
        cen_ab_component = hoc.AssembiasLeauthaud11Cens(**kwargs)
    else:
        cen_ab_component = hoc.Leauthaud11Cens(**kwargs)

    cen_model_dict = {}
    cen_model_dict['occupation'] = cen_ab_component

    # Build the profile model
    cen_profile = gpf.IsotropicGalProf(
        gal_type='centrals', halo_prof_model=hpc.TrivialProfile)
    cen_model_dict['profile'] = cen_profile

    ##############################
    ### Build the occupation model
    if satellite_assembias is True:
        sat_ab_component = hoc.AssembiasLeauthaud11Sats(**kwargs)
    else:
        sat_ab_component = hoc.Leauthaud11Sats(**kwargs)

    sat_model_dict = {}
    sat_model_dict['occupation'] = sat_ab_component

    # Build the profile model
    sat_profile = gpf.IsotropicGalProf(
        gal_type='satellites', halo_prof_model=hpc.NFWProfile)
    sat_model_dict['profile'] = sat_profile

    model_blueprint = {'centrals': cen_model_dict, 'satellites': sat_model_dict}
    return model_blueprint













