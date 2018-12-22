from ..stpipe import Step
from .. import datamodels
from . import extract


__all__ = ["Extract1dStep"]


class Extract1dStep(Step):
    """Extract a 1-d spectrum from 2-d data

    Attributes
    ----------
    ref_file : str
        Name of the reference file.  This can be "N/A" if there is no
        reference file for the current instrument mode.

    smoothing_length : int or None
        If not None, the background regions (if any) will be smoothed
        with a boxcar function of this width along the dispersion
        direction.  This should be an odd integer.

    bkg_order : int or None
        If not None, a polynomial with order `bkg_order` will be fit to
        each column (or row if the dispersion direction is horizontal)
        of the background region or regions.  For a given column (row),
        one polynomial will be fit to all background regions.  The
        polynomial will be evaluated at each pixel of the source
        extraction region(s) along the column (row), and the fitted value
        will be subtracted from the data value at that pixel.
        If both `smoothing_length` and `bkg_order` are not None, the
        boxcar smoothing will be done first.

    log_increment : int
        if `log_increment` is greater than 0 (the default is 50) and the
        input data are multi-integration (which can be CubeModel or
        SlitModel), a message will be written to the log with log level
        INFO every `log_increment` integrations.  This is intended to
        provide progress information when invoking the step interactively.
    """

    spec = """
    # Boxcar smoothing width for background regions.
    smoothing_length = integer(default=None)
    # Order of polynomial fit to one column (or row if the dispersion
    # direction is vertical) of background regions.
    bkg_order = integer(default=None, min=0)
    # Log a progress message when processing multi-integration data.
    log_increment = integer(default=50)
    """

    reference_file_types = ['extract1d']

    def process(self, input):
        """Execute the step.

        Parameters
        ----------
        input: JWST data model

        Returns
        -------
        JWST data model
            This will be `input_model` if the step was skipped; otherwise,
            it will be a model containing 1-D extracted spectra.
        """

        valid_models = (datamodels.CubeModel,
                        datamodels.ModelContainer,
                        datamodels.ImageModel,
                        datamodels.MultiSlitModel,
                        datamodels.MultiProductModel,
                        datamodels.IFUCubeModel,
                        datamodels.DrizProductModel,
                        datamodels.SlitModel)

        # Open the input and figure out what type of model it is
        input_model = datamodels.open(input)
        if isinstance(input_model, valid_models):
            self.log.debug('Input is a {0:s}'.format(input_model.meta.model_type))
        else:
            self.log.error('Input is a {0:s},'.format(type(input_model)))
            self.log.error('which was not expected for extract_1d.')
            self.log.error('extract_1d will be skipped.')
            input_model.meta.cal_step.extract_1d = 'SKIPPED'
            return input_model

        # Do the extraction
        if isinstance(input_model, datamodels.ModelContainer):
            if len(input_model) > 1:
                self.log.debug("Input contains %d items", len(input_model))
                result = datamodels.ModelContainer()
                for model in input_model:
                    if model.meta.exposure.type in extract.WFSS_EXPTYPES:
                        self.ref_file = 'N/A'
                        self.log.info('No EXTRACT1D reference file '
                                      'will be used')
                    else:
                        # Get the reference file name
                        self.ref_file = self.get_reference_file(
                                        model, 'extract1d')
                        self.log.info('Using EXTRACT1D reference file %s',
                                      self.ref_file)
                    temp = extract.do_extract1d(model, self.ref_file,
                                                self.smoothing_length,
                                                self.bkg_order,
                                                self.log_increment)
                    # Set the step flag to complete in each MultiSpecModel
                    temp.meta.cal_step.extract_1d = 'COMPLETE'
                    result.append(temp)
                    del temp
            elif len(input_model) == 1:
                if input_model[0].meta.exposure.type in extract.WFSS_EXPTYPES:
                    self.ref_file = 'N/A'
                    self.log.info('No EXTRACT1D reference file will be used')
                else:
                    # Get the reference file name for the one model in input
                    self.ref_file = self.get_reference_file(input_model[0],
                                                            'extract1d')
                    self.log.info('Using EXTRACT1D reference file %s',
                                  self.ref_file)
                result = extract.do_extract1d(input_model[0], self.ref_file,
                                              self.smoothing_length,
                                              self.bkg_order,
                                              self.log_increment)
                # Set the step flag to complete
                result.meta.cal_step.extract_1d = 'COMPLETE'
            else:
                self.log.error('Input model is empty;')
                self.log.error('extract_1d will be skipped.')
                return input_model
        else:
            # Get the reference file name
            if input_model.meta.exposure.type in extract.WFSS_EXPTYPES:
                self.ref_file = 'N/A'
                self.log.info('No EXTRACT1D reference file will be used')
            else:
                self.ref_file = self.get_reference_file(input_model,
                                                        'extract1d')
                self.log.info('Using EXTRACT1D reference file %s',
                              self.ref_file)
            result = extract.do_extract1d(input_model, self.ref_file,
                                          self.smoothing_length,
                                          self.bkg_order,
                                          self.log_increment)
            # Set the step flag to complete
            result.meta.cal_step.extract_1d = 'COMPLETE'

        input_model.close()

        return result
