"""Erros de domínio Identity — sem HTTP."""


class IdentityError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class UserNotFound(IdentityError):
    def __init__(self, key: str | int):
        super().__init__(f"Usuário {key} não encontrado", code="user_not_found")


class EmailDuplicate(IdentityError):
    def __init__(self, email: str):
        super().__init__(f"E-mail já cadastrado: {email}", code="email_duplicate")


class LastAdminGuard(IdentityError):
    def __init__(self):
        super().__init__(
            "Não é possível inativar nem alterar o papel do último administrador ativo",
            code="last_admin_guard",
        )


class SelfDeactivateForbidden(IdentityError):
    def __init__(self):
        super().__init__("Não é possível inativar o próprio usuário", code="self_deactivate")


class InvalidRole(IdentityError):
    def __init__(self, role: str | int):
        super().__init__(f"Papel inválido: {role}", code="invalid_role")


class IdentityValidationError(IdentityError):
    def __init__(self, message: str):
        super().__init__(message, code="validation_error")
