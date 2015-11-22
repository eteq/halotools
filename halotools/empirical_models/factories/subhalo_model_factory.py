# -*- coding: utf-8 -*-
"""
Module storing the various factories used to build galaxy-halo models. 
"""

__all__ = ['SubhaloModelFactory']
__author__ = ['Andrew Hearin']

import numpy as np
from copy import copy
from warnings import warn 
import collections 

from ..factories import ModelFactory, SubhaloMockFactory

from .. import model_helpers
from .. import model_defaults 

from ...sim_manager.supported_sims import HaloCatalog
from ...sim_manager import sim_defaults
from ...sim_manager.generate_random_sim import FakeSim
from ...utils.array_utils import custom_len
from ...custom_exceptions import *



class SubhaloModelFactory(ModelFactory):
    """ Class used to build models of the galaxy-halo connection in which galaxies live at the centers of subhalos.  

    The arguments passed to the `SubhaloModelFactory` constructor determine 
    the features of the model that are returned 
    by the factory. There are three sets of options for these arguments:

    * The ``model_nickname`` string argument can be used to return composite models that have already been pre-built by the Halotools package.

    * A sequence of ``model_features`` can be passed, each of which are instances of component models. In this case the factory composes these independently-defined components into a composite model. 

    * By combining the ``baseline_model_instance`` and ``model_features`` arguments, you can swap out features of the baseline composite model with new component models you pass in.  

    Regardless what set of instructions you pass to factory, the returned object can be used 
    to directly populate subhalos with mock galaxies. 

    Explicit examples of each use-case appear in the documentation below. 
    See :ref:`subhalo_model_factory_tutorial` for thorough documentation on the internals of the factory. 

    """

    def __init__(self, model_nickname = None, **kwargs):
        """
        Parameters
        ----------
        model_nickname : string, optional 
            If passed to the constructor, the appropriate prebuilt 
            model_dictionary will be used to build the instance. 
            See the ``Examples`` below. 

        *model_features : sequence of keyword arguments, optional 
            Each keyword you use will be interpreted as the name of a feature in the composite model; 
            the value bound to each keyword must be an instance of a 
            component model governing the behavior of that feature. 
            See the ``Examples`` below. 

        model_feature_calling_sequence : list, optional
            Determines the order in which your component features  
            will be called during mock population. 

            Some component models may have explicit dependence upon 
            the value of some other galaxy property being modeled. 
            In such a case, you must pass a ``model_feature_calling_sequence`` list, 
            ordered in the desired calling sequence. 

            A classic example is if the stellar-to-halo-mass relation 
            has explicit dependence on the star formation rate of the galaxy 
            (active or quiescent). For this example, the
            ``model_feature_calling_sequence`` would be 
            model_feature_calling_sequence = ['sfr_designation', 'stellar_mass', ...]. 

            Default behavior is to assume that no model feature  
            has explicit dependence upon any other, in which case the component 
            models appearing in the ``model_features`` keyword arguments 
            will be called in random order, giving primacy to the potential presence 
            of `stellar_mass` and/or `luminosity` features. 

        galaxy_selection_func : function object, optional  
            Function object that imposes a cut on the mock galaxies. 
            Function should take a length-k Astropy table as a single positional argument, 
            and return a length-k numpy boolean array that will be 
            treated as a mask over the rows of the table. If not None, 
            the mask defined by ``galaxy_selection_func`` will be applied to the 
            ``galaxy_table`` after the table is generated by the `populate_mock` method. 
            Default is None.  

        halo_selection_func : function object, optional   
            Function object used to place a cut on the input ``table``. 
            If the ``halo_selection_func`` keyword argument is passed, 
            the input to the function must be a single positional argument storing a 
            length-N structured numpy array or Astropy table; 
            the function output must be a length-N boolean array that will be used as a mask. 
            Halos that are masked will be entirely neglected during mock population.

        Examples 
        ---------
        First let's see how we can use the ``model_nickname`` argument to return the 
        pre-built `behroozi10` composite model:

        >>> model_instance = SubhaloModelFactory(model_nickname = 'behroozi10', redshift = 2)

        Passing in `behroozi10` as the ``model_nickname`` argument triggers the factory to 
        call the `~halotools.empirical_models.composite_models.smhm_models.behroozi10_model_dictionary` 
        function. When doing so, the remaining arguments that were passed to the `SubhaloModelFactory` 
        will in turn be passed on to 
        `~halotools.empirical_models.composite_models.smhm_models.behroozi10_model_dictionary`. 

        Now that we have built an instance of a composite model, we can use it to 
        populate any simulation in the Halotools cache: 

        >>> model_instance.populate_mock(simname = 'bolshoi', redshift = 2) # doctest: +SKIP

        Next we'll show an example of how to call the `~SubhaloModelFactory` using the `model_features` 
        keyword argument(s). In this next model, we'll use the 
        `~halotools.empirical_models.smhm_models.Behroozi10SmHm` class to model stellar mass, 
        and the `~halotools.empirical_models.sfr_models.BinaryGalpropModel` class to model 
        whether galaxies are quiescent or star-forming. 

        >>> from halotools.empirical_models.smhm_models import Behroozi10SmHm
        >>> stellar_mass_model = Behroozi10SmHm(redshift = 0.5)

        >>> from halotools.empirical_models.sfr_models import BinaryGalpropInterpolModel
        >>> sfr_model = BinaryGalpropInterpolModel(galprop_name = 'quiescent_designation')

        >>> model_instance = SubhaloModelFactory(stellar_mass = stellar_mass_model, sfr = sfr_model)

        In the above call to the factory, note that we do not need to pass in a 
        `mock_generation_calling_sequence` argument because in this model, neither the 
        ``quiescent_designation`` nor the ``stellar_mass`` models have explicit dependence 
        upon one another. 

        >>> model_instance.populate_mock(simname = 'bolplanck', redshift = 0.5) # doctest: +SKIP

        Notes 
        ------
        This factory is tested by the `~halotools.empirical_models.factories.tests.TestSubhaloModelFactory` class. 

        """

        input_model_dictionary, supplementary_kwargs = (
            self.parse_constructor_kwargs(model_nickname, **kwargs)
            )

        super(SubhaloModelFactory, self).__init__(input_model_dictionary, **supplementary_kwargs)
        self.mock_factory = SubhaloMockFactory

        self._model_feature_calling_sequence = (
            self.build_model_feature_calling_sequence(supplementary_kwargs))

        self.model_dictionary = collections.OrderedDict()
        for key in self._model_feature_calling_sequence:
            self.model_dictionary[key] = copy(self._input_model_dictionary[key])

        # Build up and bind several lists from the component models
        self.build_prim_sec_haloprop_list()
        self.build_publication_list()
        self.build_new_haloprop_func_dict()
        self.build_dtype_list()
        self.set_warning_suppressions()
        self.set_model_redshift()
        self.set_inherited_methods()
        self.build_init_param_dict()

        # Create a set of bound methods with specific names 
        # that will be called by the mock factory 
        self.set_primary_behaviors()
        self.set_calling_sequence()

    def parse_constructor_kwargs(self, model_nickname, **kwargs):
        """ Method used to parse the arguments passed to 
        the constructor into a model dictionary and supplementary arguments.

        The behavior is straightforward. If an input `model_nickname` was passed to `__init__`, 
        then `parse_constructor_kwargs` calls the `_retrieve_prebuilt_model_dictionary` method. 
        Otherwise, `parse_constructor_kwargs` examines the keyword arguments passed to `__init__`, 
        and identifies the possible presence of ``galaxy_selection_func``, ``halo_selection_func`` and 
        ``model_feature_calling_sequence``; all other keyword arguments will be treated as 
        component models, and it is enforced that the values bound to all such arguments 
        at the very least have a ``_methods_to_inherit`` attribute. 

        Parameters 
        -----------
        model_nickname : string 
            Nickname of the prebuilt composite model. If None, a full model dictionary 
            must be supplied with the remaining keyword arguments. If not None, 
            the string must correspond to one of the prebuilt models provided by Halotools. 

        **kwargs : optional keyword arguments 
            keywords will be interpreted as the ``feature name``; values must be instances of 
            Halotools component models 

        Returns 
        --------
        input_model_dictionary : dict 
            Model dictionary defining the composite model. 

        supplementary_kwargs : dict 
            Dictionary of any possible remaining keyword arguments passed to the `__init__` constructor 
            that are not part of the composite model dictionary, e.g., ``model_feature_calling_sequence``. 

        See also 
        ---------
        :ref:`subhalo_model_factory_parsing_kwargs`
        """
        if model_nickname is None:
            input_model_dictionary = copy(kwargs)

            ### First parse the supplementary keyword arguments, 
            # such as 'model_feature_calling_sequence', 
            ### from the keywords that are bound to component model instances, 
            # such as 'stellar_mass'

            possible_supplementary_kwargs = ('galaxy_selection_func', 
                'halo_selection_func', 'model_feature_calling_sequence')

            supplementary_kwargs = {}
            for key in possible_supplementary_kwargs:
                try:
                    supplementary_kwargs[key] = copy(input_model_dictionary[key])
                    del input_model_dictionary[key]
                except KeyError:
                    pass

            if 'model_feature_calling_sequence' not in supplementary_kwargs:
                supplementary_kwargs['model_feature_calling_sequence'] = None

            self._enforce_component_model_format(input_model_dictionary)
            return input_model_dictionary, supplementary_kwargs

        else:
            input_model_dictionary, supplementary_kwargs = (
                self._retrieve_prebuilt_model_dictionary(model_nickname, **kwargs)
                )
            return input_model_dictionary, supplementary_kwargs 

    def _enforce_component_model_format(self, candidate_model_dictionary):
        """ Private method to ensure that the input model dictionary is properly formatted.
        """
        msg_preface = ("\nYou passed the following keyword argument "
            "to the SubhaloModelFactory: ``%s``\n")
        msg_conclusion = ("See the `~halotools.empirical_models.SubhaloModelFactory` "
            "docstring for further details.\n")

        for feature_key, component_model in candidate_model_dictionary.iteritems():
            cl = component_model.__class__
            clname = cl.__name__

            if isinstance(component_model, cl):
                pass
            elif issubclass(component_model, cl):
                msg = (msg_preface + "Instead of binding an instance of ``" + clname + 
                    "`` to this keyword,\n"
                    "instead you bound the ``"+clname+"`` itself.\n"
                    "The structure of Halotools model dictionaries is strictly to accept \n"
                    "component model instances, not component model classes. \n" + msg_conclusion)
                raise HalotoolsError(msg % feature_key)

            try:
                assert hasattr(component_model, '_methods_to_inherit')
                for methodname in component_model._methods_to_inherit:
                    assert hasattr(component_model, methodname)
            except AssertionError:
                msg = (msg_preface + "You bound an instance of the ``"+clname+"`` to this keyword,\n"
                    "but the instance does not have a properly defined ``_methods_to_inherit`` attribute.\n"
                    "At a minimum, all component models must have this attribute, \n"
                    "even if there is only an empty list bound to it.\n"
                    "Any items in this list must be names of methods bound to the component model.\n" + msg_conclusion)
                raise HalotoolsError(msg % feature_key)

            try:
                assert hasattr(component_model, '_galprop_dtypes_to_allocate')
                dt = component_model._galprop_dtypes_to_allocate
                assert type(dt) == np.dtype
            except AssertionError:
                msg = (msg_preface + "You bound an instance of the ``"+clname+"`` to this keyword,\n"
                    "but the instance does not have a np.dtype object"
                    "bound to the ``_galprop_dtypes_to_allocate`` attribute.\n"
                    "At a minimum, all component models must have this attribute, \n"
                    "and it must be numpy.dtype object,"
                    "even if the dtype is empty.\n" + msg_conclusion)
                raise HalotoolsError(msg % feature_key)


    def _retrieve_prebuilt_model_dictionary(self, model_nickname, **constructor_kwargs):
        """
        """
        forbidden_constructor_kwargs = ('model_feature_calling_sequence')
        for kwarg in forbidden_constructor_kwargs:
            if kwarg in constructor_kwargs:
                msg = ("\nWhen using the HodModelFactory to build an instance of a prebuilt model,\n"
                    "do not pass a ``%s`` keyword argument to the SubhaloModelFactory constructor.\n"
                    "The appropriate source of this keyword is as part of a prebuilt model dictionary.\n")
                raise HalotoolsError(msg % kwarg)


        model_nickname = model_nickname.lower()

        if model_nickname == 'behroozi10':
            from ..composite_models import smhm_models
            dictionary_retriever = smhm_models.behroozi10_model_dictionary
        elif model_nickname == 'smhm_binary_sfr':
            from ..composite_models import sfr_models
            dictionary_retriever = sfr_models.smhm_binary_sfr_model_dictionary
        else:
            msg = ("\nThe ``%s`` model_nickname is not recognized by Halotools\n")
            raise HalotoolsError(msg)

        result = dictionary_retriever(**constructor_kwargs)
        if type(result) is dict:
            input_model_dictionary = result
            supplementary_kwargs = {}
            supplementary_kwargs['model_feature_calling_sequence'] = None 
        elif type(result) is tuple:
            input_model_dictionary = result[0]
            supplementary_kwargs = result[1]
        else:
            raise HalotoolsError("Unexpected result returned from ``%s``\n"
            "Should be either a single dictionary or a 2-element tuple of dictionaries\n"
             % dictionary_retriever.__name__)

        return input_model_dictionary, supplementary_kwargs
        
    def build_model_feature_calling_sequence(self, supplementary_kwargs):
        """ Method uses the ``model_feature_calling_sequence`` passed to __init__, if available. 
        If no such argument was passed, the method chooses a *mostly* random order for the calling sequence, 
        excepting only for cases where either there is a feature named ``stellar_mass`` or ``luminosity``, 
        which are always called first in the absence of explicit instructions to the contrary. 

        Parameters 
        -----------
        supplementary_kwargs : dict 
            Dictionary storing all keyword arguments passed to the `__init__` constructor that were 
            not part of the input model dictionary. 

        Returns 
        -------
        model_feature_calling_sequence : list 
            List of strings specifying the order in which the component models will be called upon 
            during mock population to execute their methods. 

        See also 
        ---------
        :ref:`model_feature_calling_sequence_mechanism`
        """
        ########################
        ### Require that all elements of the input model_feature_calling_sequence 
        ### were also keyword arguments to the __init__ constructor 
        try:
            model_feature_calling_sequence = list(supplementary_kwargs['model_feature_calling_sequence'])
            for model_feature in model_feature_calling_sequence:
                try:
                    assert model_feature in self._input_model_dictionary.keys()
                except AssertionError:
                    msg = ("\nYour input ``model_feature_calling_sequence`` has a ``%s`` element\n"
                    "that does not appear in the keyword arguments you passed to the SubhaloModelFactory.\n"
                    "For every element of the input ``model_feature_calling_sequence``, there must be a corresponding \n"
                    "keyword argument to which a component model instance is bound.\n")
                    raise HalotoolsError(msg % model_feature)
        except TypeError:
            # The supplementary_kwargs['model_feature_calling_sequence'] was None, triggering a TypeError, 
            # so we will use the default calling sequence instead
            # The default sequence will be to first use the centrals_occupation (if relevant), 
            # then any possible additional occupation features, then any possible remaining features
            model_feature_calling_sequence = []

            if 'stellar_mass' in self._input_model_dictionary:
                model_feature_calling_sequence.append('stellar_mass')
                remaining_keys = [key for key in self._input_model_dictionary if key != 'stellar_mass']
                model_feature_calling_sequence.extend(remaining_keys)
            elif 'luminosity' in self._input_model_dictionary:
                model_feature_calling_sequence.append('luminosity')
                remaining_keys = [key for key in self._input_model_dictionary if key != 'luminosity']
                model_feature_calling_sequence.extend(remaining_keys)
            else:
                model_feature_calling_sequence = list(self._input_model_dictionary.keys())

        ########################
        ### Now conversely require that all remaining __init__ constructor keyword arguments 
        ### appear in the model_feature_calling_sequence
        for constructor_kwarg in self._input_model_dictionary:
            try:
                assert constructor_kwarg in model_feature_calling_sequence
            except AssertionError:
                msg = ("\nYou passed ``%s`` as a keyword argument to the SubhaloModelFactory constructor.\n"
                    "This keyword argument does not appear in your input ``model_feature_calling_sequence``\n"
                    "and is otherwise not recognized.\n")
                raise HalotoolsError(msg % constructor_kwarg)
        ########################

        return model_feature_calling_sequence


    def set_inherited_methods(self):
        """ Function determines which component model methods are inherited by the composite model. 

        Each component model *should* have a `_mock_generation_calling_sequence` attribute 
        that provides the sequence of method names to call during mock population. Additionally, 
        each component *should* have a `_methods_to_inherit` attribute that determines 
        which methods will be inherited by the composite model. 
        The `_mock_generation_calling_sequence` list *should* be a subset of `_methods_to_inherit`. 
        If any of the above conditions fail, no exception will be raised during the construction 
        of the composite model. Instead, an empty list will be forcibly attached to each 
        component model for which these lists may have been missing. 
        Also, for each component model, if there are any elements of `_mock_generation_calling_sequence` 
        that were missing from `_methods_to_inherit`, all such elements will be forcibly added to 
        that component model's `_methods_to_inherit`.

        Finally, each component model *should* have an `_attrs_to_inherit` attribute that determines 
        which attributes will be inherited by the composite model. If any component models did not 
        implement the `_attrs_to_inherit`, an empty list is forcibly added to the component model. 

        After calling the set_inherited_methods method, it will be therefore be entirely safe to 
        run a for loop over each component model's `_methods_to_inherit` and `_attrs_to_inherit`, 
        even if these lists were forgotten or irrelevant to that particular component. 
        """

        _method_repetition_check = []
        _attrs_repetition_check = []

        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            # Ensure that all methods in the calling sequence are inherited
            try:
                mock_making_methods = component_model._mock_generation_calling_sequence
            except AttributeError:
                mock_making_methods = []
            try:
                inherited_methods = component_model._methods_to_inherit
            except AttributeError:
                inherited_methods = []
                component_model._methods_to_inherit = []

            missing_methods = set(mock_making_methods) - set(inherited_methods).intersection(set(mock_making_methods))
            for methodname in missing_methods:
                component_model._methods_to_inherit.append(methodname)

            _method_repetition_check.extend(component_model._methods_to_inherit)

            if not hasattr(component_model, '_attrs_to_inherit'):
                component_model._attrs_to_inherit = []

            _attrs_repetition_check.extend(component_model._attrs_to_inherit)


        # Check that we do not have any method names to inherit that appear 
        # in more than one component model
        repeated_method_msg = ("\n The method name ``%s`` appears "
            "in more than one component model.\n You should rename this method in one of your "
            "component models to disambiguate.\n")
        repeated_method_list = ([methodname for methodname, count in 
            collections.Counter(_method_repetition_check).items() if count > 1]
            )
        if repeated_method_list != []:
            example_repeated_methodname = repeated_method_list[0]
            raise HalotoolsError(repeated_method_msg % example_repeated_methodname)

        # Check that we do not have any attributes to inherit that appear 
        # in more than one component model
        repeated_attr_msg = ("\n The attribute name ``%s`` appears "
            "in more than one component model.\n "
            "Only ignore this message if you are confident "
            "that this will not result in unintended behavior\n")
        repeated_attr_list = ([attr for attr, count in 
            collections.Counter(_attrs_repetition_check).items() if count > 1]
            )
        if repeated_attr_list != []:
            example_repeated_attr = repeated_attr_list[0]
            warn(repeated_attr_msg % example_repeated_attr)

    def set_primary_behaviors(self, **kwargs):
        """ Creates names and behaviors for the primary methods of `SubhaloModelFactory` 
        that will be used by the outside world.  

        Notes 
        -----
        The new methods created here are given standardized names, 
        for consistent communication with the rest of the package. 
        This consistency is particularly important for mock-making, 
        so that the `SubhaloModelFactory` can always call the same functions 
        regardless of the complexity of the model. 

        The behaviors of the methods created here are defined elsewhere; 
        `set_primary_behaviors` just creates a symbolic link to those external behaviors. 

        See also 
        ---------
        :ref:`subhalo_model_factory_inheriting_behaviors`
        """

        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            for methodname in component_model._methods_to_inherit:
                new_method_name = methodname
                new_method_behavior = self.update_param_dict_decorator(
                    component_model, methodname)
                setattr(self, new_method_name, new_method_behavior)
                setattr(getattr(self, new_method_name), 
                    '_galprop_dtypes_to_allocate', 
                    component_model._galprop_dtypes_to_allocate)

            attrs_to_inherit = list(set(
                component_model._attrs_to_inherit))
            for attrname in attrs_to_inherit:
                new_attr_name = attrname
                attr = getattr(component_model, attrname)
                setattr(self, new_attr_name, attr)


    def update_param_dict_decorator(self, component_model, func_name):
        """ Decorator used to propagate any possible changes 
        in the composite model param_dict 
        down to the appropriate component model param_dict. 

        See also 
        ----------
        :ref:`update_param_dict_decorator_mechanism`
        
        """

        def decorated_func(*args, **kwargs):

            # Update the param_dict as necessary
            for key in self.param_dict.keys():
                if key in component_model.param_dict:
                    component_model.param_dict[key] = self.param_dict[key]

            func = getattr(component_model, func_name)
            return func(*args, **kwargs)

        return decorated_func

    def set_calling_sequence(self):
        """ Method used to determine the sequence of function calls that will be made during 
        mock population. The methods of each component model will be called one after the other, 
        and the order in which the component models are called upon to execute their methods is determined by 
        the 

        See also 
        ----------
        :ref:`model_feature_calling_sequence_mechanism`

        """
        self._mock_generation_calling_sequence = []

        missing_calling_sequence_msg = ("\nComponent models typically have a list attribute called "
            "_mock_generation_calling_sequence.\nThis list determines the methods that are called "
            "by the mock factory, and the order in which they are called.\n"
            "The ``%s`` component model has no such method.\n"
            "Only ignore this warning if you are sure this is not an error.\n")

        repeated_calling_sequence_element_msg = ("\n The method name ``%s`` that appears "
            "in the calling sequence of the \n``%s`` component model also appears in the "
            "calling sequence of another model.\nYou should rename this method in one of your "
            "component models to disambiguate.\n")

        # The model dictionary is an OrderedDict that is already appropriately structured
        feature_sequence = self.model_dictionary.keys()

        ###############
        # Loop over feature_sequence and successively append each component model's
        # calling sequence to the composite model calling sequence
        for feature in feature_sequence:
            component_model = self.model_dictionary[feature]
            if hasattr(component_model, '_mock_generation_calling_sequence'):

                component_method_list = (
                    [name for name in component_model._mock_generation_calling_sequence]
                    )

                # test to make sure we have no repeated method names
                intersection = set(component_method_list) & set(self._mock_generation_calling_sequence)
                if intersection != set():
                    methodname = list(intersection)[0]
                    t = (methodname, component_model.__class__.__name__)
                    raise HalotoolsError(repeated_calling_sequence_element_msg % t)

                self._mock_generation_calling_sequence.extend(component_method_list)
            else:
                warn(missing_calling_sequence_msg % component_model.__class__.__name__)

    def set_model_redshift(self):
        """ Method sets the redshift of the composite model, simultaneously enforcing self-consistency 
        between the the redshifts of the component models. 
        """
        msg = ("Inconsistency between the redshifts of the component models:\n"
            "    For component model 1 = ``%s``, the model has redshift = %.2f.\n"
            "    For component model 2 = ``%s``, the model has redshift = %.2f.\n")

        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            if hasattr(component_model, 'redshift'):
                redshift = component_model.redshift 
                try:
                    if redshift != existing_redshift:
                        t = (component_model.__class__.__name__, redshift, 
                            last_component.__class__.__name__, existing_redshift)
                        raise HalotoolsError(msg % t)
                except NameError:
                    existing_redshift = redshift 

            last_component = component_model

        try:
            self.redshift = redshift
        except NameError:
            self.redshift = sim_defaults.default_redshift

    def build_prim_sec_haloprop_list(self):
        """ Method builds the ``_haloprop_list`` of strings. 

        This list stores the names of all halo catalog columns 
        that appear as either ``prim_haloprop_key`` or ``sec_haloprop_key`` of any component model. 
        For all strings appearing in ``_haloprop_list``, the mock ``galaxy_table`` will have 
        a corresponding column storing the halo property inherited by the mock galaxy. 
        """
        haloprop_list = []
        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            if hasattr(component_model, 'prim_haloprop_key'):
                haloprop_list.append(component_model.prim_haloprop_key)
            if hasattr(component_model, 'sec_haloprop_key'):
                haloprop_list.append(component_model.sec_haloprop_key)

        self._haloprop_list = list(set(haloprop_list))

    def build_publication_list(self):
        """ Method collects together all publications from each of the component models. 
        """
        pub_list = []
        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            try:
                pubs = component_model.publications 
                if type(pubs) in [str, unicode]:
                    pub_list.append(pubs)
                elif type(pubs) is list:
                    pub_list.extend(pubs)
                else:
                    clname = component_model.__class__.__name__
                    msg = ("The ``publications`` attribute of the " + clname + " feature\n"
                        "must be a string or list of strings")
                    raise HalotoolsError(msg)
            except AttributeError:
                pass

        self.publications = list(set(pub_list))

    def build_new_haloprop_func_dict(self):
        """ Method used to build a dictionary of functions, ``new_haloprop_func_dict``, 
        that create new halo catalog columns 
        during a pre-processing phase of mock population. 

        See also 
        ---------
        :ref:`new_haloprop_func_dict_mechanism`
        """
        new_haloprop_func_dict = {}
        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            # Haloprop function dictionaries
            if hasattr(component_model, 'new_haloprop_func_dict'):
                dict_intersection = set(new_haloprop_func_dict).intersection(
                    set(component_model.new_haloprop_func_dict))
                if dict_intersection == set():
                    new_haloprop_func_dict = dict(
                        new_haloprop_func_dict.items() + 
                        component_model.new_haloprop_func_dict.items()
                        )
                else:
                    example_repeated_element = list(dict_intersection)[0]
                    clname = component_model.__class__.__name__
                    msg = ("The composite model received multiple "
                        "component models \nwith a new_haloprop_func_dict that use "
                        "the %s key. \nIgnoring the one that appears in the %s feature")
                    warn(msg % (example_repeated_element, clname))

        self.new_haloprop_func_dict = new_haloprop_func_dict

    def set_warning_suppressions(self):
        """ Method used to determine whether a warning should be issued if the 
        `build_init_param_dict` method detects the presence of multiple appearances 
        of the same parameter name. 

        If *any* of the component model instances have a 
        `_suppress_repeated_param_warning` attribute that is set to the boolean True value, 
        then no warning will be issued even if there are multiple appearances of the same 
        parameter name. This allows the user to not be bothered with warning messages for cases 
        where it is understood that there will be no conflicting behavior. 

        See also 
        ---------
        build_init_param_dict
        """
        self._suppress_repeated_param_warning = False
        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            if hasattr(component_model, '_suppress_repeated_param_warning'):
                self._suppress_repeated_param_warning += component_model._suppress_repeated_param_warning

    def build_init_param_dict(self):
        """ Create the `param_dict` attribute of the instance. The `param_dict` is a dictionary storing 
        the full collection of parameters controlling the behavior of the composite model. 

        The `param_dict` dictionary is determined by examining the 
        `param_dict` attribute of every component model, and building up a composite 
        dictionary from them. It is permissible for the same parameter name to appear more than once 
        amongst a set of component models, but a warning will be issued in such cases. 

        Notes 
        -----
        In MCMC applications, the items of ``param_dict`` defines the possible 
        parameter set explored by the likelihood engine. 
        Changing the values of the parameters in ``param_dict`` 
        will propagate to the behavior of the component models 
        when the relevant methods are called. 

        See also 
        ---------
        set_warning_suppressions

        :ref:`param_dict_mechanism` 

        """

        self.param_dict = {}

        try:
            suppress_warning = self._suppress_repeated_param_warning
        except AttributeError:
            suppress_warning = False
        msg = ("\n\nThe param_dict key %s appears in more than one component model.\n"
            "This is permissible, but if you are seeing this message you should be sure you "
            "understand it.\nIn particular, double-check that this parameter does not have "
            "conflicting meanings across components.\n"
            "\nIf you do not wish to see this message every time you instantiate, \n"
            "simply attach a _suppress_repeated_param_warning attribute \n"
            "to any of your component models and set this variable to ``True``.\n")

        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            if not hasattr(component_model, 'param_dict'):
                component_model.param_dict = {}

            intersection = set(self.param_dict) & set(component_model.param_dict)

            if intersection != set():
                for key in intersection:
                    if suppress_warning is False:
                        warn(msg % key)

            for key, value in component_model.param_dict.iteritems():
                self.param_dict[key] = value

        self._init_param_dict = copy(self.param_dict)

    def build_dtype_list(self):
        """ Create the `_galprop_dtypes_to_allocate` attribute that determines 
        the name and data type of every galaxy property that will appear in the mock ``galaxy_table``. 

        This attribute is determined by examining the 
        `_galprop_dtypes_to_allocate` attribute of every component model, and building a composite 
        set of all these dtypes, enforcing self-consistency in cases where the same galaxy property 
        appears more than once. 

        See also 
        ---------
        :ref:`galprop_dtypes_to_allocate_mechanism` 
        """
        dtype_list = []
        # Loop over all component features in the composite model
        for feature, component_model in self.model_dictionary.iteritems():

            # Column dtypes to add to mock galaxy_table
            if hasattr(component_model, '_galprop_dtypes_to_allocate'):
                dtype_list.append(component_model._galprop_dtypes_to_allocate)

        self._galprop_dtypes_to_allocate = model_helpers.create_composite_dtype(dtype_list)

    def restore_init_param_dict(self):
        """ Reset all values of the current ``param_dict`` to the values 
        the class was instantiated with. 

        Primary behaviors are reset as well, as this is how the 
        inherited behaviors get bound to the values in ``param_dict``. 

        See also 
        ---------
        :ref:`param_dict_mechanism` 
        """
        self.param_dict = self._init_param_dict
        self.set_primary_behaviors()
        self.set_calling_sequence()
