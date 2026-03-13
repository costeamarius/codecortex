import os
import tempfile
import unittest

from codecortex.graph_builder import build_graph


class DjangoSemanticsTests(unittest.TestCase):
    def test_build_graph_extracts_django_semantic_edges(self):
        with tempfile.TemporaryDirectory() as repo_path:
            os.makedirs(os.path.join(repo_path, "app", "portfolio"), exist_ok=True)
            os.makedirs(os.path.join(repo_path, "app", "profiles"), exist_ok=True)
            with open(os.path.join(repo_path, "app", "__init__.py"), "w", encoding="utf-8") as f:
                f.write("")
            with open(
                os.path.join(repo_path, "app", "portfolio", "__init__.py"), "w", encoding="utf-8"
            ) as f:
                f.write("")
            with open(
                os.path.join(repo_path, "app", "profiles", "__init__.py"), "w", encoding="utf-8"
            ) as f:
                f.write("")

            with open(
                os.path.join(repo_path, "app", "profiles", "models.py"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    "from django.db import models\n"
                    "\n"
                    "class PhotographerProfile(models.Model):\n"
                    "    pass\n"
                )

            with open(
                os.path.join(repo_path, "app", "portfolio", "models.py"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    "from django.db import models\n"
                    "from app.profiles.models import PhotographerProfile\n"
                    "\n"
                    "class PortfolioImagePhotographer(models.Model):\n"
                    "    profile = PhotographerProfile\n"
                )

            with open(
                os.path.join(repo_path, "app", "portfolio", "forms.py"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    "from django import forms\n"
                    "from app.portfolio.models import PortfolioImagePhotographer\n"
                    "\n"
                    "class PortfolioFormPhotographer(forms.ModelForm):\n"
                    "    class Meta:\n"
                    "        model = PortfolioImagePhotographer\n"
                )

            with open(os.path.join(repo_path, "app", "utils.py"), "w", encoding="utf-8") as f:
                f.write(
                    "def handle_portfolio_edit(**kwargs):\n"
                    "    return kwargs\n"
                )

            with open(
                os.path.join(repo_path, "app", "portfolio", "views.py"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    "from django.shortcuts import render\n"
                    "from app.portfolio.forms import PortfolioFormPhotographer\n"
                    "from app.portfolio.models import PortfolioImagePhotographer\n"
                    "from app.utils import handle_portfolio_edit\n"
                    "\n"
                    "def edit_featured_photographer(request):\n"
                    "    return handle_portfolio_edit(\n"
                    "        form_class=PortfolioFormPhotographer,\n"
                    "        model_class=PortfolioImagePhotographer,\n"
                    "        template_name='fashion/profile/edit_featured_photographer.html',\n"
                    "    )\n"
                )

            graph = build_graph(repo_path, generated_at="now", git_commit="head")
            edges = {
                (edge["from"], edge["to"], edge["type"])
                for edge in graph["edges"]
            }
            node_ids = {node["id"] for node in graph["nodes"]}

            self.assertIn("semantic:django.model", node_ids)
            self.assertIn("semantic:django.form", node_ids)
            self.assertIn("semantic:django.view", node_ids)
            self.assertIn("template:fashion/profile/edit_featured_photographer.html", node_ids)

            self.assertIn(
                (
                    "class:app.profiles.models.PhotographerProfile",
                    "semantic:django.model",
                    "is_django_model",
                ),
                edges,
            )
            self.assertIn(
                (
                    "class:app.portfolio.models.PortfolioImagePhotographer",
                    "semantic:django.model",
                    "is_django_model",
                ),
                edges,
            )
            self.assertIn(
                (
                    "class:app.portfolio.forms.PortfolioFormPhotographer",
                    "semantic:django.form",
                    "is_django_form",
                ),
                edges,
            )
            self.assertIn(
                (
                    "class:app.portfolio.forms.PortfolioFormPhotographer",
                    "class:app.portfolio.models.PortfolioImagePhotographer",
                    "binds_model",
                ),
                edges,
            )
            self.assertIn(
                (
                    "function:app.portfolio.views.edit_featured_photographer",
                    "semantic:django.view",
                    "is_django_view",
                ),
                edges,
            )
            self.assertIn(
                (
                    "function:app.portfolio.views.edit_featured_photographer",
                    "class:app.portfolio.forms.PortfolioFormPhotographer",
                    "uses_form",
                ),
                edges,
            )
            self.assertIn(
                (
                    "function:app.portfolio.views.edit_featured_photographer",
                    "class:app.portfolio.models.PortfolioImagePhotographer",
                    "uses_model",
                ),
                edges,
            )
            self.assertIn(
                (
                    "function:app.portfolio.views.edit_featured_photographer",
                    "function:app.utils.handle_portfolio_edit",
                    "delegates_to",
                ),
                edges,
            )
            self.assertIn(
                (
                    "function:app.portfolio.views.edit_featured_photographer",
                    "template:fashion/profile/edit_featured_photographer.html",
                    "uses_template",
                ),
                edges,
            )


if __name__ == "__main__":
    unittest.main()
