import 'package:flutter/material.dart';

enum _DocType { quotation, order, receipt, invoice, issue }

class ProcurementScreen extends StatefulWidget {
  const ProcurementScreen({super.key});

  @override
  State<ProcurementScreen> createState() => _ProcurementScreenState();
}

class _ProcurementScreenState extends State<ProcurementScreen> {
  void _open(_DocType type) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _DocForm(type: type),
    );
  }

  Widget _card(String title, IconData icon, VoidCallback onTap) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        trailing: const Icon(Icons.arrow_forward_ios),
        onTap: onTap,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('إدارة المشتريات والمخازن')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _card('عرض سعر جديد', Icons.request_quote, () => _open(_DocType.quotation)),
          _card('أمر شراء جديد', Icons.shopping_cart_checkout, () => _open(_DocType.order)),
          _card('إذن استلام', Icons.move_to_inbox, () => _open(_DocType.receipt)),
          _card('فاتورة شراء', Icons.receipt_long, () => _open(_DocType.invoice)),
          _card('إذن صرف', Icons.outbox, () => _open(_DocType.issue)),
        ],
      ),
    );
  }
}

class _DocForm extends StatefulWidget {
  final _DocType type;
  const _DocForm({required this.type});

  @override
  State<_DocForm> createState() => _DocFormState();
}

class _DocFormState extends State<_DocForm> {
  final no = TextEditingController();
  final qty = TextEditingController();
  final price = TextEditingController();
  final batch = TextEditingController();
  final expiry = TextEditingController();
  final vat = TextEditingController(text: '14');

  bool vatOn = true;
  bool saving = false;

  void save() async {
    setState(() => saving = true);
    try {
      await Future.delayed(const Duration(seconds: 1));
      if (mounted) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  String get title {
    switch (widget.type) {
      case _DocType.quotation:
        return 'عرض سعر';
      case _DocType.order:
        return 'أمر شراء';
      case _DocType.receipt:
        return 'إذن استلام';
      case _DocType.invoice:
        return 'فاتورة شراء';
      case _DocType.issue:
        return 'إذن صرف';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Expanded(child: Text('إضافة $title', style: Theme.of(context).textTheme.titleLarge)),
                IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
              ],
            ),
            TextField(controller: no, decoration: const InputDecoration(labelText: 'رقم المستند')),
            Row(
              children: [
                Expanded(child: TextField(controller: qty, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'الكمية'))),
                const SizedBox(width: 10),
                Expanded(child: TextField(controller: price, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'السعر الصافي'))),
              ],
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: saving ? null : save,
                icon: saving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.save),
                label: Text(saving ? 'جاري الحفظ...' : 'حفظ المستند'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
