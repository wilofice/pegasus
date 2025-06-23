import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

class NotificationService {
  final FirebaseMessaging _fcm = FirebaseMessaging.instance;

  Future<void> init() async {
    await _fcm.requestPermission();
    FirebaseMessaging.onBackgroundMessage(_backgroundHandler);
    FirebaseMessaging.onMessage.listen(_onMessage);
    FirebaseMessaging.onMessageOpenedApp.listen(_onMessageOpenedApp);
    await _fcm.getToken();
  }

  static Future<void> _backgroundHandler(RemoteMessage message) async {
    // handle background notifications
    debugPrint('Background notification: ${message.messageId}');
  }

  void _onMessage(RemoteMessage message) {
    debugPrint('Foreground notification: ${message.notification?.title}');
  }

  void _onMessageOpenedApp(RemoteMessage message) {
    debugPrint('Notification opened: ${message.data}');
  }
}
