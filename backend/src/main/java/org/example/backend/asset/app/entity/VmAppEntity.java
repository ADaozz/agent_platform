package org.example.backend.asset.app.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;
import lombok.EqualsAndHashCode;
import lombok.experimental.Accessors;
import org.springframework.format.annotation.DateTimeFormat;

import java.util.Date;

@Data
@TableName("vm_app")
@Accessors(chain = true)
@EqualsAndHashCode(callSuper = false)
public class VmAppEntity {

    @TableId(type = IdType.ASSIGN_UUID)
    // 应用 ID（UUID）
    private String appId;

    // 应用名称
    private String appName;

    // 所属虚机 ID，关联 vm_host.host_id
    private String hostId;

    // 所属虚机 IP（冗余字段，与虚机 vm_ip 同步）
    private String vmIp;

    // 应用部署路径
    private String deployPath;

    // 应用状态：running-运行中，stopped-已停止
    private String appStatus;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 创建时间
    private Date createTime;

    @JsonFormat(timezone = "GMT+8", pattern = "yyyy-MM-dd HH:mm:ss")
    @DateTimeFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    // 更新时间
    private Date updateTime;
}
