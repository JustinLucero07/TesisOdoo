# Evidencia de Pruebas (Plan y Resultados)

**Proyecto:** Sistema de gestión inmobiliaria sobre ERP Odoo 19.
**Tipo de pruebas:** unitarias y de integración automatizadas (framework de pruebas nativo de Odoo, basado en `unittest` / `TransactionCase`).

---

## 1. Estrategia de pruebas

Las pruebas se ejecutan dentro de transacciones aisladas que se revierten al finalizar (no contaminan la base de datos). Se verifican:

- **Restricciones de datos** (`@api.constrains`): montos, fechas, rangos válidos.
- **Máquinas de estado**: transiciones válidas e inválidas de contratos.
- **Lógica de negocio**: cálculo de match presupuestal, scoring, comisiones.
- **Campos calculados y relacionados**: AVM, datos de visita, KPIs de reportes.
- **Seguridad**: confidencialidad de documentos por rol.
- **Integraciones**: validación de tokens de webhook, parsing de estadísticas.

---

## 2. Cómo ejecutar las pruebas

```bash
source /home/justin/Documentos/Tesis/venv19/bin/activate

# Todas las pruebas de los módulos personalizados
python /home/justin/Documentos/odoo19/odoo-bin -c odoo19.conf -d tesis_odoo19 \
  --test-enable --stop-after-init \
  -u estate_management,estate_crm,estate_calendar,estate_document,\
estate_reports,estate_social,estate_wordpress

# Pruebas de un solo módulo
python /home/justin/Documentos/odoo19/odoo-bin -c odoo19.conf -d tesis_odoo19 \
  --test-enable --stop-after-init -u estate_calendar
```

---

## 3. Resultado de la ejecución

> **Ejecución completa: `0 failed, 0 error(s) of 129 tests`** ✅

| Módulo | Archivo de pruebas | Casos | Enfoque |
|--------|--------------------|:-----:|---------|
| estate_management | test_estate_property.py | 14 | Restricciones de propiedad (año, precio mínimo, comisión, estado inicial, índices) |
| estate_management | test_contract_state_machine.py | 11 | Transiciones de estado del contrato y renovaciones |
| estate_management | test_estate_contract.py | 6 | Validación de monto y fechas de contrato |
| estate_management | test_estate_offer.py | 6 | Validación de ofertas (monto, expiración) |
| estate_management | test_estate_payment.py | 3 | Validación de monto de pago |
| estate_management | test_phone_mixin.py | 8 | Normalización de números telefónicos |
| estate_crm | test_match_percentage.py | 12 | Cálculo de coincidencia presupuesto/propiedad |
| estate_crm | test_negotiation_strategy.py | 4 | Estrategia de negociación según match |
| estate_crm | test_meta_dedup.py | 8 | Deduplicación de eventos de webhook Meta |
| estate_calendar | test_calendar.py | 8 | Visitas: cliente, datos relacionados, color, estados, encuesta |
| estate_document | test_document_lifecycle.py | 11 | Ciclo de vida y validación de archivos |
| estate_document | test_document_confidentiality.py | 6 | Confidencialidad por rol |
| estate_document | test_document_contract_integration.py | 5 | Documentos placeholder al activar contrato |
| estate_reports | test_sales_report_wizard.py | 14 | KPIs de ventas, % vs listado, export XLSX |
| estate_social | test_facebook_stats.py | 7 | Parsing de estadísticas de Facebook |
| estate_wordpress | test_webhook_token.py | 6 | Validación de token de webhook |
| **TOTAL** | **16 archivos** | **129** | |

---

## 4. Casos destacados (muestra)

### 4.1. Regresión — campo Cliente de la visita (`estate_calendar`)
Verifica que el cliente asignado a una visita **se conserve** y no sea sobreescrito por el organizador (corrige una colisión de nombre con el campo base `partner_id` de Odoo).

```python
def test_client_id_persists(self):
    ev = self._make_visit()
    self.assertEqual(ev.client_id, self.client)      # cliente correcto
    self.assertEqual(ev.partner_id, ev.user_id.partner_id)  # organizador intacto
```

### 4.2. Máquina de estados del contrato (`estate_management`)
Valida que una transición inválida lance error y que la renovación genere un contrato hijo.

```python
def test_invalid_transition_raises(self): ...
def test_create_renewal_creates_child_contract(self): ...
```

### 4.3. Match presupuestal (`estate_crm`)
Comprueba el algoritmo de coincidencia entre el presupuesto del cliente y la propiedad (incluye penalización por tipo, ciudad y habitaciones).

```python
def test_perfect_match_100(self): ...
def test_budget_too_low_zero_score(self): ...
```

---

## 5. Conclusión

El sistema cuenta con **129 pruebas automatizadas** distribuidas en los principales módulos, **todas en estado verde**. Estas pruebas constituyen evidencia objetiva de la correcta operación de la lógica de negocio y sirven como red de seguridad ante futuros cambios (pruebas de regresión).

> Este documento, junto con el log de ejecución, se incluye como **anexo de verificación** del proyecto.

---

*Evidencia de Pruebas — Proyecto de Titulación, UPS Sede Cuenca.*
