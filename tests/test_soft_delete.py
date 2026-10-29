"""Django pack, `soft-delete-read` (slice 008): a read of a model whose rows can be
soft-deleted, with no deletion flag anywhere in the query. The models are found by reading
the project's code, never listed by hand (D-022)."""

import pytest

from healthkit import cli
from healthkit.findings import ToolError, ToolSkipped
from healthkit.tools import django

# A made-up project: every case the rule must tell apart.
SHOP_MODELS = """\
from django.db import models
from safedelete.managers import SafeDeleteManager


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    objects = SoftDeleteManager()

    class Meta:
        abstract = True


class Product(SoftDeleteModel):  # flag inherited from a base in the repo
    name = models.CharField(max_length=50)


class Order(models.Model):  # its own flag, Django's default manager
    is_deleted = models.BooleanField(default=False)


class Invoice(SoftDeleteModel):  # a manager that already hides deleted rows
    objects = LiveManager()


class Coupon(models.Model):  # a manager from an outside package: cannot be read
    is_deleted = models.BooleanField(default=False)
    objects = SafeDeleteManager()


class Customer(models.Model):  # no flag at all
    name = models.CharField(max_length=50)
"""


def findings(repo, code: str, models: str = SHOP_MODELS) -> list[tuple[int, str]]:
    repo.write("shop/models.py", models)
    repo.write("shop/views.py", code)
    return sorted((f.line, f.message.split()[0]) for f in django.run(repo.root, ["shop/views.py"]))


def test_reads_without_the_flag_are_flagged(repo):
    code = """\
a = Product.objects.filter(name="x")
b = Order.objects.get(id=1)
c = get_object_or_404(Product, id=1)
"""
    assert findings(repo, code) == [(1, "Product"), (2, "Order"), (3, "Product")]


def test_reads_that_name_the_flag_or_cannot_see_deleted_rows_are_quiet(repo):
    code = """\
a = Product.objects.filter(name="x", is_deleted=False)
b = Product.objects.filter(name="x").filter(is_deleted=False)
c = Product.objects.filter(Q(is_deleted=False) | Q(name="x"))
d = Order.objects.filter(is_deleted__in=[False])
e = Order.objects.filter(**live)
f = Product.objects.filter(id=1).update(name="y")
g = Order.objects.filter(id=1).delete()
h = get_object_or_404(Product, id=1, is_deleted=False)
i = Customer.objects.get(id=1)
j = Invoice.objects.get(id=1)
k = Product.objects.all()
"""
    assert findings(repo, code) == []


def test_a_chain_that_starts_elsewhere_is_still_read_whole(repo):
    # QuickRPA ac8a630^ storage_buckets/api/storage_buckets.py:704 (shape: select_related first).
    code = """\
robot = Product.objects.select_related("work_space").get(
    id=robot_id, work_space__in=permitted_ws,
)
"""
    assert findings(repo, code) == [(1, "Product")]


def test_models_with_an_unreadable_manager_are_named_not_hidden(repo):
    findings(repo, "x = Coupon.objects.get(id=1)\n")

    assert django.notes(repo.root) == [
        "django: not checked for soft-delete-read: Coupon (manager from outside the repo)"
    ]


def test_models_are_found_outside_models_py(repo):
    # gtech-mulearn/mulearnbackend keeps its models in db/*.py: a file-name convention
    # found none of its soft-delete models (slice 008, second-project measurement).
    repo.write("db/task.py", SHOP_MODELS)
    repo.write("api/views.py", "a = Order.objects.get(id=1)\n")

    assert [f.line for f in django.run(repo.root, ["api/views.py"])] == [1]


def test_the_flag_name_comes_from_the_project(repo):
    repo.write(".healthkit/config.toml", '[django]\nsoft_delete_fields = ["deleted_at"]\n')
    models = """\
from django.db import models


class Post(models.Model):
    deleted_at = models.DateTimeField(null=True)
"""
    code = "a = Post.objects.get(id=1)\nb = Post.objects.get(id=1, deleted_at__isnull=True)\n"

    assert findings(repo, code, models) == [(1, "Post")]


def test_a_field_the_delete_method_clears_counts_as_the_flag(repo):
    # QuickRPA studio_robot/models.py:1164: RobotVersion.soft_delete() sets is_active=False,
    # so `filter(is_active=True)` can never return a deleted version (22 of 99 findings in
    # the first QuickRPA measurement were this shape).
    models = (
        SHOP_MODELS
        + """

class Version(SoftDeleteModel):
    is_active = models.BooleanField(default=False)

    def soft_delete(self):
        self.is_active = False
        super().soft_delete()
"""
    )
    models = models.replace(
        "    objects = SoftDeleteManager()\n\n    class Meta:",
        "    objects = SoftDeleteManager()\n\n"
        "    def soft_delete(self):\n        self.is_deleted = True\n        self.save()\n\n"
        "    class Meta:",
    )
    code = """\
a = Version.objects.filter(is_active=True).first()
b = Version.objects.filter(is_active=False)
c = Product.objects.filter(is_active=True)
"""
    assert findings(repo, code, models) == [(2, "Version"), (3, "Product")]


def test_projections_and_admin_scripts_are_not_checked(repo):
    # First QuickRPA hand-read (20 findings, 25% real): ids and names pulled for scoping
    # (`values_list("id")`) and one-off admin scripts were never the bug. An existence
    # check stays checked: f0a3b4e's door was `filter(...).exists()`.
    code = """\
a = Product.objects.filter(name="x").values_list("id", flat=True)
b = Product.objects.filter(name="x").values("name")
c = Product.objects.filter(id=1).exists()
"""
    assert findings(repo, code) == [(3, "Product")]
    repo.write("shop/management/commands/seed.py", "x = Product.objects.get(id=1)\n")
    assert django.run(repo.root, ["shop/management/commands/seed.py"]) == []


def test_test_files_are_not_checked(repo):
    # Tests read deleted rows on purpose (22 of 99 in the first QuickRPA measurement).
    read = "x = Product.objects.get(id=1)\n"
    repo.write("shop/models.py", SHOP_MODELS)
    test_files = [
        "shop/tests.py",
        "shop/tests_api.py",
        "shop/test_views.py",
        "shop/views_test.py",
        "shop/tests/helpers.py",
    ]
    for path in test_files:
        repo.write(path, read)

    assert django.run(repo.root, test_files) == []


def test_a_model_file_that_does_not_parse_is_never_a_pass(repo):
    with pytest.raises(ToolError, match=r"shop/models\.py"):
        findings(repo, "x = 1\n", models="class Broken(models.Model):\n    x = (\n")


def test_a_project_without_django_models_is_skipped_out_loud(repo):
    repo.write("app.py", "x = 1\n")

    with pytest.raises(ToolSkipped, match="no Django models"):
        django.run(repo.root, ["app.py"])


# ── Real incidents (QuickRPA history): each parent line flagged, each fix quiet ──────────

# QuickRPA commons/managers.py and commons/models.py:39 (dev 7fadfe3), trimmed.
QUICKRPA_MODELS = """\
from django.db import models


class SoftDeleteManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset()


class SoftDeleteModel(models.Model):
    '''Abstract model for implementing soft delete protocol'''
    is_deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()


class Robot(TimeStampModel, UserStampModel, SoftDeleteModel):
    name = models.CharField(max_length=255)
"""
INCIDENTS = {
    # e938910 "Hide archived robots from workspace listings": organization/api/organization.py:524
    "e938910": (
        "    queryset = (\n        Robot.objects.filter(work_space=ws)\n    )\n",
        "    queryset = (\n        Robot.objects.filter(work_space=ws, is_deleted=False)\n    )\n",
    ),
    # f0a3b4e: vault/api/vault.py:610, _get_robot_in_workspace
    "f0a3b4e": (
        (
            "    try:\n        return Robot.objects.get(id=robot_pk, work_space=ws)\n"
            "    except Robot.DoesNotExist:\n        raise\n"
        ),
        (
            "    try:\n"
            "        return Robot.objects.get(id=robot_pk, work_space=ws, is_deleted=False)\n"
            "    except Robot.DoesNotExist:\n        raise\n"
        ),
    ),
    # ac8a630: storage_buckets/api/storage_buckets.py:704, _resolve_bucket_move_target
    "ac8a630": (
        (
            '    robot = Robot.objects.select_related("work_space").get(\n'
            "        id=robot_id, work_space__in=permitted_ws,\n    )\n"
        ),
        (
            '    robot = Robot.objects.select_related("work_space").get(\n'
            "        id=robot_id, work_space__in=permitted_ws, is_deleted=False,\n    )\n"
        ),
    ),
}


@pytest.mark.parametrize("incident", sorted(INCIDENTS))
def test_real_incidents_are_caught_and_their_fixes_are_quiet(repo, incident):
    before, after = INCIDENTS[incident]

    flagged = findings(repo, f"def view(ws):\n{before}", QUICKRPA_MODELS)
    assert [model for _, model in flagged] == ["Robot"]
    assert findings(repo, f"def view(ws):\n{after}", QUICKRPA_MODELS) == []


def test_the_review_shows_it_on_changed_lines_only_and_never_blocks(repo, capsys):
    # Advisory (slice 008): about half its findings were real bugs on code it was never
    # tuned on (QuickRPA held-out 41%, mulearnbackend 55%), under the 70% a blocking rule
    # needs. Shown so a person looks; never a failed gate.
    repo.write("shop/models.py", SHOP_MODELS)
    old = "from shop.models import Order, Product\n\nold = Order.objects.get(id=1)\n"
    repo.write("shop/views.py", old)
    base = repo.commit("base")
    repo.write("shop/views.py", f"{old}new = Product.objects.get(id=2)\n")
    repo.commit()

    code = cli.main(["review", "--base", base])

    out = capsys.readouterr().out
    assert code == 0, out
    assert "worth a look: shop/views.py:4: [django soft-delete-read] Product" in out
    assert "worth a look: 1" in out
    assert "shop/views.py:3:" not in out  # an old line is not this branch's problem
    assert "not checked for soft-delete-read: Coupon" in out
