#  -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2019-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE URL <https://store.webkul.com/license.html/> for full copyright and licensing details.
#################################################################################
import logging
_logger = logging.getLogger(__name__)
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
	_inherit = 'product.template'
	
	def _compute_quantities_dict(self):
		res = super(ProductTemplate, self)._compute_quantities_dict()
		if len(self) > 1:
			pass
		else:
			ACT_VARIANTS = self.mapped('product_variant_ids')
			variants_available = self.mapped('product_variant_ids')._product_available()
			prod_available = {}
			for template in self:
				qty_available = 0
				virtual_available = 0
				incoming_qty = 0
				outgoing_qty = 0
				for p in template.product_variant_ids:
					qty_available += variants_available[p.id]["qty_available"]
					virtual_available += variants_available[p.id]["virtual_available"]
					incoming_qty += variants_available[p.id]["incoming_qty"]
					outgoing_qty += variants_available[p.id]["outgoing_qty"]
					################################### CODE ADDED BY JAHANGIR ####################################
					if template.is_pack and template.wk_product_pack:

						if len(template.product_variant_ids) > 1:
							variants_list = template.product_variant_ids.ids
						else:
							variants_list = [template.product_variant_ids.id]
						for pp in template.wk_product_pack:
							variants_list.append(pp.product_id.id)
						
						variants = self.env['product.product'].browse(variants_list)
						variants_available.update(variants._product_available())
						qty_avail = []
						vir_avail = []
						inco_qty = []
						outgo_qty = []
						for pp in template.wk_product_pack:
							if pp.product_id and pp.product_quantity > 0 and pp.product_id.type not in ['consu','service']:
								qty_avail.append(variants_available[pp.product_id.id]["qty_available"]/pp.product_quantity)
								vir_avail.append(variants_available[pp.product_id.id]["virtual_available"]/pp.product_quantity)
								inco_qty.append(variants_available[pp.product_id.id]["incoming_qty"]/pp.product_quantity)
								outgo_qty.append(variants_available[pp.product_id.id]["outgoing_qty"]/pp.product_quantity)
						qty_available = min(qty_avail)
						virtual_available = min(vir_avail)
						incoming_qty = min(inco_qty)
						outgoing_qty = min(outgo_qty)
						template.product_variant_ids = ACT_VARIANTS
				################################### CODE CLOSED BY JAHANGIR ####################################
				prod_available[template.id] = {
					"qty_available": qty_available,
					"virtual_available": virtual_available,
					"incoming_qty": incoming_qty,
					"outgoing_qty": outgoing_qty,
				}

			return prod_available
		return res

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'
	
	def _compute_qty_delivered(self):
		res = super(SaleOrderLine, self)._compute_qty_delivered()
		for line in self:
			
			if line.product_id.is_pack:
				delivered_qty = []
				bundle_product_id = []
				if all([m.state == 'done' for m in line.move_ids]):
					line.qty_delivered = line.product_uom_qty
					line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
				else:
					for bundle_product in line.product_id.wk_product_pack:
						bundle_product_id.append(bundle_product.product_id.id)

					for delivery in line.order_id.picking_ids:
						if not delivery.backorder_id:
							for product_move in line.move_ids:
								if product_move.product_id.is_pack:
									line.qty_deliverd = product_move.quantity_done
								else:
									if product_move.product_id.id in bundle_product_id:
										bundle_item = line.product_id.wk_product_pack.filtered(lambda obj: obj.product_id.id == product_move.product_id.id)
										qty = int(product_move.quantity_done/bundle_item.product_quantity)
										delivered_qty.append(qty)

							if len(delivered_qty) != 0:
								line.qty_delivered = max(delivered_qty)
								line.qty_to_invoice = line.qty_delivered
		return res
	
	@api.depends('product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.warehouse_id', 'order_id.commitment_date')
	def _compute_qty_at_date(self):
		res = super(SaleOrderLine,self)._compute_qty_at_date()
		
		for line in self:
			if line.product_id.is_pack:
				prod_available = line.product_id.product_tmpl_id._compute_quantities_dict()
				available_quantities = prod_available[line.product_id.product_tmpl_id.id]
				line.free_qty_today = available_quantities.get('qty_available',0)
				line.virtual_available_at_date = available_quantities.get('virtual_available',0)
		
		return res