import 'package:flutter/material.dart';
import '../services/api_client.dart';

class AccountingScreen extends StatefulWidget {
  final ApiClient api;
  const AccountingScreen({super.key, required this.api});
  @override State<AccountingScreen> createState() => _AccountingScreenState();
}

class _AccountingScreenState extends State<AccountingScreen> {
  List<dynamic> accounts = [];
  bool loading = true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => loading = true);
    final a = await widget.api.getList('accounts');
    if (mounted) setState(() { accounts = a; loading = false; });
  }

  void _showImportDialog() {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('استيراد شجرة الحسابات / مراكز التكلفة'),
        content: const Text(
          'يدعم النظام استيراد شجرة الحسابات ومراكز التكلفة مباشرة عبر ملفات Excel / CSV '
          'باستخدام نموذج الأعمدة المخزنة (Code, Name, Account_Type, Is_Postable).

'
          'يمكنك استخدام مسار API الخاص بالاستيراد:
'
          '/api/accounts/import-csv
'
          '/api/cost-centers/import-csv'
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('حسناً'))
        ],
      ),
    );
  }

  @override Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('دليل الحسابات والمالية'),
        actions: [
          IconButton(
            icon: const Icon(Icons.file_upload),
            tooltip: 'استيراد Excel/CSV',
            onPressed: _showImportDialog,
          )
        ],
      ),
      body: loading ? const Center(child: CircularProgressIndicator()) : ListView.builder(
        itemCount: accounts.length,
        itemBuilder: (_, i) {
          final acc = accounts[i];
          return ListTile(
            leading: const Icon(Icons.account_balance_wallet, color: Colors.blue),
            title: Text('${acc['code']} - ${acc['name']}'),
            subtitle: Text('النوع: ${acc['account_type']} | قابل للترحيل: ${acc['is_postable'] ?? true}'),
          );
        },
      ),
    );
  }
}
