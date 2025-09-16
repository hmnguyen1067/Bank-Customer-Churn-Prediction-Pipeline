import api.loader as loader


def test_get_latest_version_none(monkeypatch):
    class FakeClient:
        def search_model_versions(self, q):  # noqa: ARG002
            return []

    assert loader._get_latest_version(FakeClient(), "any") is None


def test_get_latest_version_max(monkeypatch):
    class V:
        def __init__(self, v):
            self.version = v

    class FakeClient:
        def search_model_versions(self, q):  # noqa: ARG002
            return [V("1"), V("3"), V("2")]

    assert loader._get_latest_version(FakeClient(), "name") == 3


# def test_load_bundle_loads_models_and_metadata(monkeypatch):
#     import mlflow

#     class DummyPreproc:
#         pass

#     class DummyModel:
#         pass

#     monkeypatch.setattr(mlflow.sklearn, "load_model", lambda *a, **k: DummyPreproc())
#     monkeypatch.setattr(mlflow.xgboost, "load_model", lambda *a, **k: DummyModel())

#     # Stub MlflowClient
#     class V:
#         def __init__(self, v):
#             self.version = v

#     class FakeClient:
#         def search_model_versions(self, q):  # noqa: ARG002
#             return [V("2"), V("5")]

#     monkeypatch.setattr(loader, "MlflowClient", lambda: FakeClient())

#     bundle = loader.load_bundle(
#         tracking_uri="http://stub", preprocessor_name="PP", model_name="MODEL"
#     )
#     assert bundle is not None
#     assert isinstance(bundle.preprocessor, DummyPreproc)
#     assert isinstance(bundle.model, DummyModel)
#     assert bundle.feature_order == list(CATEGORICAL_FEATURES) + list(NUMERICAL_FEATURES)
#     assert bundle.metadata["preprocessor"]["name"] == "PP"
#     assert bundle.metadata["model"]["version"] == 5
