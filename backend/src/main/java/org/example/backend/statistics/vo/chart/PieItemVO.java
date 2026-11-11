package org.example.backend.statistics.vo.chart;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 对应 ECharts pie series.data 单项：{ name, value }。
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PieItemVO {

    private String name;

    private Long value;
}
