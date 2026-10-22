from django.db import NotSupportedError, models


class ExactQuantityField(models.DecimalField):
    """Keep precision intact until the ledger's database checks validate it.

    numeric(p,s) rounds before constraints run. Unconstrained numeric plus explicit
    range/precision checks rejects nonrepresentable quantities instead.
    """

    def db_type(self, connection):
        if connection.vendor != "postgresql":
            raise NotSupportedError("Exact stock quantities require PostgreSQL")
        return "numeric"
