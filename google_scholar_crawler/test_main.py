import unittest
from unittest.mock import patch

import main


class SerpApiConversionTest(unittest.TestCase):
    def test_converts_author_response_to_existing_site_schema(self):
        response = {
            "search_metadata": {"status": "Success"},
            "author": {
                "name": "Example Author",
                "affiliations": "Example University",
                "email": "Verified email at example.edu",
                "interests": [{"title": "Machine Learning"}],
                "thumbnail": "https://example.test/photo.jpg",
            },
            "articles": [
                {
                    "title": "Example Paper",
                    "citation_id": "author-id:paper-id",
                    "publication": "Example Journal, 2026",
                    "year": "2026",
                    "cited_by": {
                        "value": 7,
                        "link": "https://scholar.google.com/scholar?cites=123",
                        "cites_id": "123",
                    },
                }
            ],
            "cited_by": {
                "table": [
                    {"citations": {"all": 7, "since_2021": 7}},
                    {"h_index": {"all": 1, "since_2021": 1}},
                    {"i10_index": {"all": 0, "since_2021": 0}},
                ],
                "graph": [{"year": 2026, "citations": 7}],
            },
        }

        with patch.object(main, "serpapi_request", return_value=response):
            author = main.fetch_with_serpapi("secret", "author-id")

        self.assertEqual(author["citedby"], 7)
        self.assertEqual(author["hindex"], 1)
        self.assertEqual(author["cites_per_year"], {"2026": 7})
        publication = author["publications"]["author-id:paper-id"]
        self.assertEqual(publication["num_citations"], 7)
        self.assertEqual(publication["bib"]["title"], "Example Paper")


if __name__ == "__main__":
    unittest.main()
