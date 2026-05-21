/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { PropertySummary } from "./components/property_summary/property_summary";

// Register the component so the Chatter template can use <PropertySummary/>
Object.assign(Chatter.components, { PropertySummary });
