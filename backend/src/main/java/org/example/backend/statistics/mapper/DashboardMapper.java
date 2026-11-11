package org.example.backend.statistics.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface DashboardMapper {

    @Select("SELECT COUNT(*) FROM public.sys_user")
    Long countUsers();

    @Select("<script>"
            + "SELECT lifecycle_status AS name, COUNT(*) AS value FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if> "
            + "GROUP BY lifecycle_status"
            + "</script>")
    List<CountGroupRow> countVmByLifecycle(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT env AS name, COUNT(*) AS value FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if> "
            + "GROUP BY env"
            + "</script>")
    List<CountGroupRow> countVmByEnv(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT network_zone AS name, COUNT(*) AS value FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if> "
            + "GROUP BY network_zone"
            + "</script>")
    List<CountGroupRow> countVmByNetworkZone(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT a.app_status AS name, COUNT(*) AS value FROM vm_app a "
            + "INNER JOIN vm_host h ON a.host_id = h.host_id "
            + "<if test='ownerUserId != null'>WHERE h.owner_user_id = #{ownerUserId}</if> "
            + "GROUP BY a.app_status"
            + "</script>")
    List<CountGroupRow> countAppByStatus(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT COUNT(*) FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if>"
            + "</script>")
    Long countVmHost(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT COUNT(*) FROM vm_host WHERE lifecycle_status = 'running' "
            + "<if test='ownerUserId != null'>AND owner_user_id = #{ownerUserId}</if>"
            + "</script>")
    Long countVmHostRunning(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT COALESCE(SUM(cpu_cores), 0) FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if>"
            + "</script>")
    Long sumCpuCores(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT COALESCE(SUM(memory_gb), 0) FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if>"
            + "</script>")
    Long sumMemoryGb(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT COUNT(*) FROM vm_app a INNER JOIN vm_host h ON a.host_id = h.host_id "
            + "<if test='ownerUserId != null'>WHERE h.owner_user_id = #{ownerUserId}</if>"
            + "</script>")
    Long countVmApp(@Param("ownerUserId") Long ownerUserId);

    @Select("<script>"
            + "SELECT TO_CHAR(create_time, 'YYYY-MM') AS name, COUNT(*) AS value FROM vm_host "
            + "<if test='ownerUserId != null'>WHERE owner_user_id = #{ownerUserId}</if> "
            + "GROUP BY TO_CHAR(create_time, 'YYYY-MM') ORDER BY name"
            + "</script>")
    List<CountGroupRow> countVmCreateTrend(@Param("ownerUserId") Long ownerUserId);

    @Select("SELECT u.user_name AS name, COUNT(*) AS value FROM vm_host h "
            + "INNER JOIN public.sys_user u ON h.owner_user_id = u.user_id "
            + "GROUP BY u.user_name ORDER BY value DESC LIMIT 10")
    List<CountGroupRow> countVmByOwner();

    @Select("SELECT physical_host_ip AS name, COUNT(*) AS value FROM vm_host "
            + "GROUP BY physical_host_ip ORDER BY value DESC LIMIT 10")
    List<CountGroupRow> countVmByPhysicalHost();
}
