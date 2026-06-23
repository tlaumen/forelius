class PlottingError(ValueError):
    pass


class PlotDataError(PlottingError):
    pass


class PlotIntentError(PlottingError):
    pass


class PlotRenderingError(PlottingError):
    pass
