"""Modelos partilhados do projecto (re-exporta soft delete de mixins)."""
from app.mixins import SoftDeleteModel, SoftDeleteManager, SoftDeleteAllManager

__all__ = ['SoftDeleteModel', 'SoftDeleteManager', 'SoftDeleteAllManager']
