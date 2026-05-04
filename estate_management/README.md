# estate_management — Núcleo Inmobiliario

Módulo base del sistema. Define las entidades centrales del negocio: propiedades, contratos, pagos, comisiones, ofertas, depósitos y sus interacciones.

## Modelos clave

| Modelo | Propósito |
|---|---|
| `estate.property` | Propiedad inmobiliaria. Estados: `available → reserved → sold/rented`. Incluye AVM, QR, días en mercado, sync WP/Social. |
| `estate.contract` | Contratos de venta o alquiler vinculados a propiedad y partner. |
| `estate.payment` | Pagos del contrato. Genera factura en `account.move`. |
| `estate.property.offer` | Ofertas hechas sobre propiedades. |
| `estate.commission` | Comisiones a co-asesores y aliados externos. |
| `estate.contract.deposit` | Depósitos de garantía (arriendo). |
| `estate.appraisal` | Avalúos manuales y AVM automatizado. |
| `estate.property.tag` / `estate.property.type` | Catálogo de etiquetas y tipos. |
| `estate.phone.mixin` | **Mixin abstracto** para normalización telefónica E.164 (Ecuador). |

## Dependencias
Solo módulos estándar de Odoo (`base`, `mail`, `account`, `product`, `sale`).

## Configuración necesaria
- Grupos de usuario: `estate_group_agent`, `estate_group_manager`, `estate_group_admin` (creados en `security/`).
- Cron de recordatorio de contratos: configurable en *Ajustes → Técnico → Acciones planificadas*.

## Características destacadas
- **AVM (Automated Valuation Model)**: estima precio justo en función de comparables.
- **QR code** auto-generado por propiedad (visible en ficha y reportes).
- **Smart buttons** en `res.partner` para ver propiedades, contratos y pagos del cliente.
- **Constraints + onchange** para validar año, precios y comisiones antes y al guardar.
- **Índices BD** en campos de búsqueda frecuente (`wp_post_id`, `fb_post_id`, `phone`, `email`).

## Tests
`estate_management/tests/` — 47 tests cubriendo constraints, mixin telefónico y reglas de negocio.

```bash
python odoo-bin -c odoo19.conf -d tesis_odoo19 \
  --test-enable --stop-after-init -u estate_management
```
