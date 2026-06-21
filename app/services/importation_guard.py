from app.models import ImportationOrder


class ImportationLockedError(Exception):
    pass


def is_importation_locked(imp: ImportationOrder) -> bool:
    return imp.current_status == "CLOSED"


def assert_importation_editable(imp: ImportationOrder) -> None:
    if is_importation_locked(imp):
        raise ImportationLockedError("Importação fechada — reabra antes de editar")
