import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class NotificationService {
  final FirebaseMessaging _fcm = FirebaseMessaging.instance;

  Future<void> init() async {
    await Firebase.initializeApp();
    await _fcm.requestPermission();
    FirebaseMessaging.onBackgroundMessage(_backgroundHandler);
    FirebaseMessaging.onMessage.listen(_onMessage);
    FirebaseMessaging.onMessageOpenedApp.listen(_onMessage);
    final token = await _fcm.getToken();
    if (token != null) {
      // In a real app, send the token to the backend
      // ignore: avoid_print
      print('FCM Token: $token');
    }
  }

  static Future<void> _backgroundHandler(RemoteMessage message) async {
    await Firebase.initializeApp();
    // handle background notifications
  }

  void _onMessage(RemoteMessage message) {
    // handle foreground notifications
  }
}
