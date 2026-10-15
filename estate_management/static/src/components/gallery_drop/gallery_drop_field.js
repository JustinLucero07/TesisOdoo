/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useFileUploader } from "@web/core/utils/files";
import { useState } from "@odoo/owl";
import {
    Many2ManyBinaryField,
    many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";

const ACEPTADOS = ["image/", "video/"];

/**
 * Zona de carga de fotos y videos de la propiedad.
 *
 * Igual que many2many_binary, pero toda la zona es clicable y admite soltar
 * archivos encima. Al guardar la propiedad, las fotos pasan a la galería y los
 * videos a su propia sección (ver _sync_gallery_to_images).
 */
export class GalleryDropField extends Many2ManyBinaryField {
    static template = "estate_management.GalleryDropField";

    setup() {
        super.setup();
        this.uploadFiles = useFileUploader();
        // Contador y no booleano: dragenter/dragleave se disparan también al
        // pasar por encima de los elementos hijos, y con un booleano el
        // resaltado parpadeaba.
        this.dropState = useState({ depth: 0 });
    }

    get dragging() {
        return this.dropState.depth > 0;
    }

    get pendingSummary() {
        const fotos = this.files.filter((f) => (f.mimetype || "").startsWith("image/")).length;
        const videos = this.files.filter((f) => (f.mimetype || "").startsWith("video/")).length;
        const partes = [];
        if (fotos) {
            partes.push(`${fotos} ${fotos === 1 ? "foto" : "fotos"}`);
        }
        if (videos) {
            partes.push(`${videos} ${videos === 1 ? "video" : "videos"}`);
        }
        return partes.join(" y ") || `${this.files.length} archivos`;
    }

    onDragEnter(ev) {
        ev.preventDefault();
        this.dropState.depth++;
    }

    onDragOver(ev) {
        ev.preventDefault();
    }

    onDragLeave(ev) {
        ev.preventDefault();
        this.dropState.depth = Math.max(0, this.dropState.depth - 1);
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.dropState.depth = 0;
        if (this.props.readonly) {
            return;
        }
        const files = [...(ev.dataTransfer ? ev.dataTransfer.files : [])].filter((f) =>
            ACEPTADOS.some((tipo) => f.type.startsWith(tipo))
        );
        if (!files.length) {
            return;
        }
        const params = {
            csrf_token: odoo.csrf_token,
            ufile: files,
            model: this.props.record.resModel,
            id: this.props.record.resId || 0,
        };
        const parsedFileData = await this.uploadFiles("/web/binary/upload_attachment", params);
        if (parsedFileData) {
            await this.onFileUploaded(parsedFileData);
        }
    }
}

export const galleryDropField = {
    ...many2ManyBinaryField,
    component: GalleryDropField,
};

registry.category("fields").add("gallery_drop", galleryDropField);
