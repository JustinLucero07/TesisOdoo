/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml, useState } from "@odoo/owl";

export class MortgageCalculator extends Component {
    static template = xml`
        <div class="o_mortgage_calculator" style="max-width:720px; margin:0 auto; padding:24px;">
            <div style="border-bottom:3px solid #1B4F72; padding-bottom:14px; margin-bottom:28px;">
                <h2 style="color:#1B4F72; margin:0; font-size:22px;">
                    <i class="fa fa-calculator"/> Calculadora de Hipoteca
                </h2>
                <p style="color:#666; margin:6px 0 0 0; font-size:13px;">
                    Estima tu cuota mensual y el costo total del crédito hipotecario.
                </p>
            </div>

            <!-- Inputs con sliders -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-bottom:28px;">

                <!-- Precio del inmueble -->
                <div class="o_field_widget" style="background:#f8f9fa; border-radius:8px; padding:18px;">
                    <label style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:6px;">
                        Precio del Inmueble
                    </label>
                    <div style="font-size:24px; font-weight:700; color:#1B4F72; margin-bottom:10px;">
                        $<t t-out="formatNumber(state.propertyPrice)"/>
                    </div>
                    <input type="range"
                           t-model.number="state.propertyPrice"
                           min="10000" max="500000" step="5000"
                           style="width:100%; accent-color:#1B4F72;"/>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#aaa; margin-top:4px;">
                        <span>$10.000</span><span>$500.000</span>
                    </div>
                </div>

                <!-- Entrada / Enganche -->
                <div class="o_field_widget" style="background:#f8f9fa; border-radius:8px; padding:18px;">
                    <label style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:6px;">
                        Entrada
                    </label>
                    <div style="font-size:24px; font-weight:700; color:#1B4F72; margin-bottom:10px;">
                        <t t-out="state.downPaymentPct"/>% — $<t t-out="formatNumber(downPaymentAmount)"/>
                    </div>
                    <input type="range"
                           t-model.number="state.downPaymentPct"
                           min="5" max="60" step="1"
                           style="width:100%; accent-color:#1B4F72;"/>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#aaa; margin-top:4px;">
                        <span>5%</span><span>60%</span>
                    </div>
                </div>

                <!-- Tasa de interés anual -->
                <div class="o_field_widget" style="background:#f8f9fa; border-radius:8px; padding:18px;">
                    <label style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:6px;">
                        Tasa de Interés Anual
                    </label>
                    <div style="font-size:24px; font-weight:700; color:#1B4F72; margin-bottom:10px;">
                        <t t-out="state.annualRate"/>%
                    </div>
                    <input type="range"
                           t-model.number="state.annualRate"
                           min="1" max="25" step="0.1"
                           style="width:100%; accent-color:#1B4F72;"/>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#aaa; margin-top:4px;">
                        <span>1%</span><span>25%</span>
                    </div>
                </div>

                <!-- Plazo en años -->
                <div class="o_field_widget" style="background:#f8f9fa; border-radius:8px; padding:18px;">
                    <label style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:0.5px; display:block; margin-bottom:6px;">
                        Plazo del Crédito
                    </label>
                    <div style="font-size:24px; font-weight:700; color:#1B4F72; margin-bottom:10px;">
                        <t t-out="state.termYears"/> años
                    </div>
                    <input type="range"
                           t-model.number="state.termYears"
                           min="1" max="30" step="1"
                           style="width:100%; accent-color:#1B4F72;"/>
                    <div style="display:flex; justify-content:space-between; font-size:11px; color:#aaa; margin-top:4px;">
                        <span>1 año</span><span>30 años</span>
                    </div>
                </div>
            </div>

            <!-- Resultados -->
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-bottom:28px;">
                <div style="background:#1B4F72; color:white; border-radius:10px; padding:20px; text-align:center;">
                    <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; opacity:0.8; margin-bottom:6px;">
                        Cuota Mensual
                    </div>
                    <div style="font-size:28px; font-weight:800;">
                        $<t t-out="formatNumber(monthlyPayment)"/>
                    </div>
                </div>
                <div style="background:#eaf4fb; border:2px solid #2E86C1; border-radius:10px; padding:20px; text-align:center;">
                    <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#555; margin-bottom:6px;">
                        Total a Pagar
                    </div>
                    <div style="font-size:22px; font-weight:700; color:#1B4F72;">
                        $<t t-out="formatNumber(totalPayment)"/>
                    </div>
                </div>
                <div style="background:#fef9e7; border:2px solid #f39c12; border-radius:10px; padding:20px; text-align:center;">
                    <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#555; margin-bottom:6px;">
                        Total Intereses
                    </div>
                    <div style="font-size:22px; font-weight:700; color:#b7770d;">
                        $<t t-out="formatNumber(totalInterest)"/>
                    </div>
                </div>
            </div>

            <!-- Desglose del préstamo -->
            <div style="background:#f8f9fa; border-radius:8px; padding:18px; font-size:13px;">
                <div style="font-weight:600; color:#1B4F72; margin-bottom:12px; font-size:14px;">
                    Desglose del Préstamo
                </div>
                <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #e0e0e0;">
                    <span style="color:#555;">Precio del inmueble</span>
                    <strong>$<t t-out="formatNumber(state.propertyPrice)"/></strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #e0e0e0;">
                    <span style="color:#555;">Entrada (<t t-out="state.downPaymentPct"/>%)</span>
                    <strong style="color:#1e8449;">— $<t t-out="formatNumber(downPaymentAmount)"/></strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #e0e0e0;">
                    <span style="color:#555;">Monto del crédito</span>
                    <strong>$<t t-out="formatNumber(loanAmount)"/></strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #e0e0e0;">
                    <span style="color:#555;">Tasa mensual</span>
                    <strong><t t-out="(state.annualRate / 12).toFixed(3)"/>%</strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:8px 0;">
                    <span style="color:#555;">Número de cuotas</span>
                    <strong><t t-out="state.termYears * 12"/> cuotas</strong>
                </div>
            </div>

            <div style="margin-top:16px; font-size:11px; color:#aaa; text-align:center;">
                * Cálculo referencial bajo el método de amortización francesa (cuota fija).
                Consulta con tu asesor financiero para condiciones reales.
            </div>
        </div>
    `;

    setup() {
        this.state = useState({
            propertyPrice: 120000,
            downPaymentPct: 20,
            annualRate: 8.5,
            termYears: 15,
        });
    }

    get downPaymentAmount() {
        return this.state.propertyPrice * (this.state.downPaymentPct / 100);
    }

    get loanAmount() {
        return this.state.propertyPrice - this.downPaymentAmount;
    }

    get monthlyPayment() {
        const r = this.state.annualRate / 100 / 12;
        const n = this.state.termYears * 12;
        const P = this.loanAmount;
        if (r === 0) return P / n;
        return P * (r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    }

    get totalPayment() {
        return this.monthlyPayment * this.state.termYears * 12;
    }

    get totalInterest() {
        return this.totalPayment - this.loanAmount;
    }

    formatNumber(value) {
        return value.toLocaleString("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
}

// Registrar como client action
registry.category("actions").add("estate_mortgage_calculator", MortgageCalculator);
