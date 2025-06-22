import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme.dart';
import 'screens/chat_screen.dart';
import 'services/notification_service.dart';

final _notificationService = NotificationService();

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await _notificationService.init();
  runApp(const ProviderScope(child: PegasusApp()));
}

class PegasusApp extends StatelessWidget {
  const PegasusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pegasus',
      theme: appTheme,
      home: const ChatScreen(),
    );
  }
}
