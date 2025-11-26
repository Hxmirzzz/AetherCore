class DomainException(Exception):
    """Excepción base del dominio"""
    pass

class EntityValidationException(DomainException):
    """Excepción para validaciones de entidades"""
    pass

class ValueObjectValidationException(DomainException):
    """Excepción para validaciones de value objects"""
    pass