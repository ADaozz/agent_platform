package org.example.backend.auth.session.constant;

public final class SessionRedisKeys {

    private static final String SESSION_PREFIX = "personal-demo:session:";
    private static final String USER_SESSION_PREFIX = "personal-demo:user-active-session:";

    private SessionRedisKeys() {
    }

    public static String session(String sessionId){
        return SESSION_PREFIX + sessionId;
    }

    public static String userSession(Long userId){
        return USER_SESSION_PREFIX + userId;
    }
}
