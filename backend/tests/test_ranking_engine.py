"""Behavioral tests for ranking.py pure-logic functions."""
import pytest
from datetime import datetime, timedelta, timezone

from app.search.ranking import (
    BM25Ranker,
    TFIDFRanker,
    PositionAwareRanker,
    MLRanker,
    DiversityRanker,
    HybridRanker,
    RankingModelManager,
    RankingFeatures,
)


@pytest.fixture
def sample_docs():
    return [
        {"title": "Python tutorial", "snippet": "Learn Python programming basics", "url": "https://example.com/python"},
        {"title": "Java guide", "snippet": "Java programming for beginners", "url": "https://example.com/java"},
        {"title": "Python advanced", "snippet": "Advanced Python techniques", "url": "https://example.com/python-adv"},
    ]


@pytest.fixture
def sample_doc():
    return {"title": "Python tutorial", "snippet": "Learn Python programming basics", "url": "https://example.com/python"}


class TestBM25Ranker:
    def test_index_documents(self, sample_docs):
        ranker = BM25Ranker()
        ranker.index_documents(sample_docs)
        assert ranker.doc_count == 3
        assert ranker.avg_doc_length > 0

    def test_index_empty_documents(self):
        ranker = BM25Ranker()
        ranker.index_documents([])
        assert ranker.doc_count == 0
        assert ranker.avg_doc_length == 0

    def test_score_no_indexed_docs(self, sample_doc):
        ranker = BM25Ranker()
        score = ranker.score("python", sample_doc)
        assert score == 0.0

    def test_score_with_match(self, sample_docs, sample_doc):
        ranker = BM25Ranker()
        ranker.index_documents(sample_docs)
        score = ranker.score("python", sample_doc)
        assert score > 0.0

    def test_score_no_match(self, sample_docs):
        ranker = BM25Ranker()
        ranker.index_documents(sample_docs)
        doc = {"title": "Ruby", "snippet": "Ruby on Rails"}
        score = ranker.score("python", doc)
        assert score == 0.0


class TestTFIDFRanker:
    def test_calculate_tf(self):
        ranker = TFIDFRanker()
        tf = ranker.calculate_tf("python", "python python java")
        assert tf == pytest.approx(2 / 3)

    def test_calculate_tf_empty_text(self):
        ranker = TFIDFRanker()
        tf = ranker.calculate_tf("python", "")
        assert tf == 0.0

    def test_calculate_idf(self, sample_docs):
        ranker = TFIDFRanker()
        idf = ranker.calculate_idf("python", sample_docs)
        assert idf > 0.0

    def test_calculate_idf_empty_docs(self):
        ranker = TFIDFRanker()
        idf = ranker.calculate_idf("python", [])
        assert idf == 0.0

    def test_calculate_idf_not_found(self, sample_docs):
        ranker = TFIDFRanker()
        idf = ranker.calculate_idf("ruby", sample_docs)
        assert idf == 0.0

    def test_calculate_idf_cached(self, sample_docs):
        ranker = TFIDFRanker()
        idf1 = ranker.calculate_idf("python", sample_docs)
        idf2 = ranker.calculate_idf("python", sample_docs)
        assert idf1 == idf2

    def test_score(self, sample_docs, sample_doc):
        ranker = TFIDFRanker()
        score = ranker.score("python", sample_doc, sample_docs)
        assert score > 0.0


class TestPositionAwareRanker:
    def test_score_title_match(self, sample_doc):
        ranker = PositionAwareRanker()
        score = ranker.score("python", sample_doc)
        assert score > 0.0

    def test_score_no_match(self):
        ranker = PositionAwareRanker()
        doc = {"title": "Ruby", "snippet": "Ruby on Rails", "url": "https://ruby.com"}
        score = ranker.score("python", doc)
        assert score == 0.0

    def test_score_url_match(self):
        ranker = PositionAwareRanker()
        doc = {"title": "Guide", "snippet": "Programming guide", "url": "https://python.org/tutorial"}
        score = ranker.score("python", doc)
        assert score > 0.0


class TestMLRanker:
    def test_extract_features(self, sample_docs, sample_doc):
        ranker = MLRanker()
        features = ranker.extract_features("python", sample_doc, sample_docs)
        assert isinstance(features, RankingFeatures)
        assert features.bm25_score >= 0.0
        assert features.title_match is True

    def test_extract_features_with_user_profile_dict(self, sample_docs, sample_doc):
        ranker = MLRanker()
        profile = {"interests": ["python"], "click_count": 5}
        features = ranker.extract_features("python", sample_doc, sample_docs, profile)
        assert features.personalization_score > 0.0
        assert features.previous_clicks == 5

    def test_extract_features_with_user_profile_obj(self, sample_docs, sample_doc):
        class MockProfile:
            interests = ["python"]
            click_count = 3
        ranker = MLRanker()
        features = ranker.extract_features("python", sample_doc, sample_docs, MockProfile())
        assert features.personalization_score > 0.0
        assert features.previous_clicks == 3

    def test_calculate_freshness_recent(self):
        ranker = MLRanker()
        doc = {"published_date": datetime.now(timezone.utc).isoformat()}
        score = ranker._calculate_freshness(doc)
        assert score > 0.9

    def test_calculate_freshness_old(self):
        ranker = MLRanker()
        doc = {"published_date": (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()}
        score = ranker._calculate_freshness(doc)
        assert score < 0.1

    def test_calculate_freshness_unknown(self):
        ranker = MLRanker()
        score = ranker._calculate_freshness({})
        assert score == 0.5

    def test_calculate_freshness_datetime_obj(self):
        ranker = MLRanker()
        doc = {"published_date": datetime.now(timezone.utc)}
        score = ranker._calculate_freshness(doc)
        assert score > 0.9

    def test_calculate_freshness_invalid_type(self):
        ranker = MLRanker()
        doc = {"published_date": 12345}
        score = ranker._calculate_freshness(doc)
        assert score == 0.5

    def test_calculate_freshness_created_at(self):
        ranker = MLRanker()
        doc = {"created_at": datetime.now(timezone.utc).isoformat()}
        score = ranker._calculate_freshness(doc)
        assert score > 0.9

    def test_calculate_domain_authority_high(self):
        ranker = MLRanker()
        doc = {"url": "https://github.com/repo"}
        score = ranker._calculate_domain_authority(doc)
        assert score == 0.9

    def test_calculate_domain_authority_default(self):
        ranker = MLRanker()
        doc = {"url": "https://random-site.com"}
        score = ranker._calculate_domain_authority(doc)
        assert score == 0.5

    def test_score(self, sample_docs, sample_doc):
        ranker = MLRanker()
        score = ranker.score("python", sample_doc, sample_docs)
        assert 0.0 <= score <= 1.0


class TestDiversityRanker:
    def test_diversify_empty(self):
        ranker = DiversityRanker()
        assert ranker.diversify([], "query") == []

    def test_diversify_single(self):
        ranker = DiversityRanker()
        results = [{"title": "Test", "snippet": "Test"}]
        assert ranker.diversify(results, "query") == results

    def test_diversify_multiple(self):
        ranker = DiversityRanker()
        results = [
            {"title": "Python", "snippet": "Python tutorial", "score": 1.0},
            {"title": "Python", "snippet": "Python tutorial", "score": 0.9},
            {"title": "Java", "snippet": "Java guide", "score": 0.8},
        ]
        diversified = ranker.diversify(results, "python", top_k=3)
        assert len(diversified) == 3

    def test_similarity_identical(self):
        ranker = DiversityRanker()
        doc1 = {"title": "Python", "snippet": "Python tutorial"}
        doc2 = {"title": "Python", "snippet": "Python tutorial"}
        sim = ranker._similarity(doc1, doc2)
        assert sim == 1.0

    def test_similarity_different(self):
        ranker = DiversityRanker()
        doc1 = {"title": "Python", "snippet": "Python tutorial"}
        doc2 = {"title": "Java", "snippet": "Java guide"}
        sim = ranker._similarity(doc1, doc2)
        assert sim == 0.0

    def test_similarity_empty(self):
        ranker = DiversityRanker()
        doc1 = {"title": "", "snippet": ""}
        doc2 = {"title": "Java", "snippet": "Java guide"}
        sim = ranker._similarity(doc1, doc2)
        assert sim == 0.0


class TestHybridRanker:
    @pytest.mark.asyncio
    async def test_rank_empty(self):
        ranker = HybridRanker()
        assert await ranker.rank("query", []) == []

    @pytest.mark.asyncio
    async def test_rank_basic(self, sample_docs):
        ranker = HybridRanker()
        results = await ranker.rank("python", sample_docs)
        assert len(results) == 3
        assert all("rank_position" in r for r in results)
        assert all("final_score" in r for r in results)

    @pytest.mark.asyncio
    async def test_rank_no_diversity(self, sample_docs):
        ranker = HybridRanker()
        results = await ranker.rank("python", sample_docs, enable_diversity=False)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rank_with_user_profile(self, sample_docs):
        ranker = HybridRanker()
        profile = {"interests": ["python"], "click_count": 5}
        results = await ranker.rank("python", sample_docs, user_profile=profile)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rank_with_personalization_engine(self, sample_docs):
        class MockPersonalizationEngine:
            def calculate_result_score_adjustment(self, profile, result):
                return 0.1
        ranker = HybridRanker(personalization_engine=MockPersonalizationEngine())
        profile = {"interests": ["python"]}
        results = await ranker.rank("python", sample_docs, user_profile=profile)
        assert len(results) == 3
        assert all("personalization_adjustment" in r for r in results)

    def test_update_statistics(self):
        ranker = HybridRanker()
        ranker._update_statistics([0.5, 0.6, 0.7])
        assert ranker.feature_stats["total_ranked"] == 3
        assert ranker.feature_stats["avg_score"] > 0


class TestRankingModelManager:
    def test_record_training_sample(self):
        manager = RankingModelManager()
        features = RankingFeatures()
        manager.record_training_sample("query", {"title": "test"}, features, True)
        assert len(manager.training_data) == 1

    def test_should_retrain_false(self):
        manager = RankingModelManager()
        assert manager.should_retrain() is False

    def test_should_retrain_true(self):
        manager = RankingModelManager()
        manager.training_data = [{}] * 1001
        assert manager.should_retrain() is True

    def test_clear_training_data(self):
        manager = RankingModelManager()
        manager.training_data = [{"data": "test"}]
        manager.clear_training_data()
        assert len(manager.training_data) == 0

    def test_get_model_info(self):
        manager = RankingModelManager()
        info = manager.get_model_info()
        assert "version" in info
        assert "training_samples" in info
        assert "feature_weights" in info
        assert "needs_retraining" in info

    def test_update_weights(self):
        manager = RankingModelManager()
        manager.update_weights({"bm25": 0.5})
        assert manager.ml_ranker.weights["bm25"] == 0.5
        assert manager.model_metadata["last_training_date"] is not None