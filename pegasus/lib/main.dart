import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme.dart';
import 'screens/home_screen.dart';
import 'screens/transcript_screen.dart';
import 'services/notification_service.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';

final _notificationService = NotificationService();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  _notificationService.init();
  runApp(const ProviderScope(child: PegasusApp()));
}

class PegasusApp extends StatelessWidget {
  const PegasusApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pegasus',
      theme: appTheme,
      darkTheme: darkAppTheme,
      themeMode: ThemeMode.system,
      home: const HomeScreen(),
      routes: {
        '/transcript': (context) {
          final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
          final audioId = args?['audioId'] as String?;
          if (audioId == null) {
            return const Scaffold(
              body: Center(child: Text('Invalid audio ID')),
            );
          }
          return TranscriptScreen(audioId: audioId);
        },
      },
    );
  }
}
