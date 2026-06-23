/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useFileUploader } from "@web/core/utils/files";
import { useState } from "@odoo/owl";
import {
    Many2ManyBinaryField,
    many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";

/**
 * Igual que el widget many2many_binary pero con zona de arrastrar-y-soltar.
 * Soltar imagenes las sube con el mismo mecanismo que el boton de adjuntar.
 */
export class GalleryDropField extends Many2ManyBinaryField {
    static template = "estate_management.GalleryDropField";

    setup() {
        super.setup();
        this.uploadFiles = useFileUploader();
        this.dropState = useState({ dragging: false });
    }

    onDragOver(ev) {
        ev.preventDefault();
        this.dropState.dragging = true;
    }

    onDragLeave(ev) {
        ev.preventDefault();
        this.dropState.dragging = false;
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.dropState.dragging = false;
        const files = [...(ev.dataTransfer ? ev.dataTransfer.files : [])].filter((f) =>
            f.type.startsWith("image/")
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
