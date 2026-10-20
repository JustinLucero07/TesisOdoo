import 'package:flutter/material.dart';

import '../crm/lead_model.dart';
import 'reminder_form_screen.dart';

/// Abre un recordatorio nuevo ya ligado al lead (cliente, propiedad y lead
/// llenos). Lo usan la tarjeta del embudo, la lista y el detalle del lead.
/// Devuelve true si se guardó.
Future<bool> openNewReminderForLead(BuildContext context, Lead lead) async {
  final messenger = ScaffoldMessenger.of(context);
  final saved = await Navigator.of(context).push<bool>(
    MaterialPageRoute(
      builder: (_) => ReminderFormScreen(
        initialPartnerId: lead.partnerId,
        initialPartnerName: lead.partnerName,
        initialPropertyId: lead.targetPropertyId,
        initialPropertyName: lead.targetPropertyName,
        initialLeadId: lead.id,
      ),
    ),
  );
  if (saved == true) {
    messenger.showSnackBar(
      const SnackBar(content: Text('Recordatorio guardado')),
    );
  }
  return saved == true;
}
