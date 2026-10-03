import 'package:flutter_test/flutter_test.dart';
import 'package:agri_erp_mobile/main.dart';

void main() {
  testWidgets('Agri ERP opens', (tester) async {
    await tester.pumpWidget(const AgriERPApp());
    expect(find.text('Agri ERP'), findsOneWidget);
    expect(find.text('المزارع'), findsOneWidget);
    expect(find.text('التصدير'), findsOneWidget);
  });
}
