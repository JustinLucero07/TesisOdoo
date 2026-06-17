/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { PropertySummary } from "./components/property_summary/property_summary";
import { DocumentPdfPreview } from "./components/document_preview/document_preview";
import { ContractPdfPreview } from "./components/document_preview/contract_preview";

// Registrar los componentes para que el template del Chatter pueda usarlos
Object.assign(Chatter.components, { PropertySummary, DocumentPdfPreview, ContractPdfPreview });
