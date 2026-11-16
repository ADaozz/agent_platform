package org.example.backend.agent.controller;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AgentRuntimeTimeoutTest {

    @Test
    void classifiesSseAndFilePaths() {
        assertTrue(AgentRuntimeController.isSsePath("/api/agent/sessions/abc/events"));
        assertFalse(AgentRuntimeController.isSsePath("/api/agent/sessions/abc"));
        assertTrue(AgentRuntimeController.isFilePath("/api/agent/sessions/abc/files/out.docx"));
        assertTrue(AgentRuntimeController.isFilePath("/api/agent/files"));
        assertTrue(AgentRuntimeController.isEventStream("text/event-stream"));
    }

    @Test
    void resolveReadTimeoutUsesDedicatedBudgets() throws Exception {
        AgentRuntimeController controller = new AgentRuntimeController();
        Field connect = AgentRuntimeController.class.getDeclaredField("connectTimeoutMs");
        Field read = AgentRuntimeController.class.getDeclaredField("readTimeoutMs");
        Field sse = AgentRuntimeController.class.getDeclaredField("sseReadTimeoutMs");
        Field file = AgentRuntimeController.class.getDeclaredField("fileReadTimeoutMs");
        for (Field field : new Field[]{connect, read, sse, file}) {
            field.setAccessible(true);
        }
        connect.setInt(controller, 5000);
        read.setInt(controller, 60000);
        sse.setInt(controller, 0);
        file.setInt(controller, 300000);

        assertEquals(0, controller.resolveReadTimeout("/api/agent/sessions/1/events", null));
        assertEquals(300000, controller.resolveReadTimeout("/api/agent/sessions/1/files/a.bin", null));
        assertEquals(60000, controller.resolveReadTimeout("/api/agent/sessions/1", "application/json"));
        assertEquals(0, controller.resolveReadTimeout("/api/agent/sessions/1", "text/event-stream"));
    }
}
