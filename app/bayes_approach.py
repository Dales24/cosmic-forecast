from pgmpy.models import BayesianModel
from pgmpy.estimators import BayesianEstimator

model = BayesianModel(
    [("Temperature", "FireRisk"), ("NDVI", "FireRisk"), ("Wind", "FireRisk")]
)
