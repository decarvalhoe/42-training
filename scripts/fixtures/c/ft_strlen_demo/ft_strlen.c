/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strlen.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: gemini <gemini@student.42lausanne.ch>      +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/03/29 00:00:00 by gemini            #+#    #+#             */
/*   Updated: 2026/03/29 00:00:00 by gemini           ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_strlen.h"

int	ft_strlen(const char *str)
{
	int	index;

	index = 0;
	while (str[index] != '\0')
		index++;
	return (index);
}
